package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

type ManifestEntry struct {
	Args           int      `json:"args"`
	ArgNames       []string `json:"arg_names"`
	Short          string   `json:"short"`
	Desc           string   `json:"desc"`
	RequiresWindow bool     `json:"requires_window"`
	File           string   `json:"file,omitempty"`
	Exe            string   `json:"exe,omitempty"`
	Deps           []string `json:"deps,omitempty"`
	Runtime        string   `json:"runtime"`
	Handler        string   `json:"handler,omitempty"`
}

type manifest map[string]ManifestEntry

type Command interface {
	Metadata() ManifestEntry
	Run(ctx *Context, args []string) error
}

type Context struct {
	Root     string
	RealCWD  string
	Manifest manifest
}

func (ctx *Context) Mark(label string, source string) {
	mark(label, true, source)
}

func (ctx *Context) MarkDetail(label string, source string) {
	mark(label, false, source)
}

func (ctx *Context) Log(message string, source string) {
	logDebug(message, true, source)
}

func (ctx *Context) LogDetail(message string, source string) {
	logDebug(message, false, source)
}

type CommandError struct {
	Title   string
	Message string
	Entry   ManifestEntry
	Cause   error
}

func (err *CommandError) Error() string {
	return err.Message
}

type debugSettings struct {
	showMarks    bool
	showLogs     bool
	verboseMarks bool
	verboseLogs  bool
}

var debugModes = map[string]debugSettings{
	"off":    {showMarks: false, showLogs: false, verboseMarks: false, verboseLogs: false},
	"lite":   {showMarks: true, showLogs: true, verboseMarks: false, verboseLogs: false},
	"normal": {showMarks: true, showLogs: true, verboseMarks: false, verboseLogs: false},
	"speed":  {showMarks: true, showLogs: false, verboseMarks: true, verboseLogs: false},
	"hard":   {showMarks: true, showLogs: true, verboseMarks: true, verboseLogs: true},
}

var debugMode = "off"
var debugStart time.Time
var debugLast time.Time

var (
	styleHelpHeader = lipgloss.NewStyle().
			Background(lipgloss.Color("15")).
			Foreground(lipgloss.Color("0")).
			Padding(0, 1)
	styleCommandHeader = lipgloss.NewStyle().
				Background(lipgloss.Color("4")).
				Foreground(lipgloss.Color("15")).
				Bold(true).
				Padding(0, 2)
	styleCommandName = lipgloss.NewStyle().Foreground(lipgloss.Color("2"))
	styleShort       = lipgloss.NewStyle().Foreground(lipgloss.Color("6"))
	styleRuntime     = lipgloss.NewStyle().Foreground(lipgloss.Color("4"))
	styleDesc        = lipgloss.NewStyle().Foreground(lipgloss.Color("3"))
	styleArgs        = lipgloss.NewStyle().Foreground(lipgloss.Color("5"))
	styleErrorTitle  = lipgloss.NewStyle().
				Background(lipgloss.Color("4")).
				Foreground(lipgloss.Color("15")).
				Bold(true).
				Padding(0, 1)
	styleErrorLabel = lipgloss.NewStyle().
			Background(lipgloss.Color("6")).
			Foreground(lipgloss.Color("0")).
			Padding(0, 1)
	styleTraceLabel = lipgloss.NewStyle().
			Background(lipgloss.Color("5")).
			Foreground(lipgloss.Color("0")).
			Padding(0, 1)
	styleMissing = lipgloss.NewStyle().Foreground(lipgloss.Color("1"))
)

var goCommandRegistry = map[string]Command{
	"help":    HelpCommand{},
	"install": InstallCommand{},
}

func main() {
	callerCWD, _ := os.Getwd()
	args, selectedDebugMode := stripDebugFlags(os.Args[1:])
	configureDebug(selectedDebugMode)
	mark("Start wutil Go core", true, "wutil-go")
	logDebug(fmt.Sprintf("debug mode set to %s", debugMode), true, "wutil-go")

	root, err := findRoot()
	if err != nil {
		exitErr(err)
	}
	logDebug(fmt.Sprintf("resolved root=%s caller_cwd=%s", root, callerCWD), false, "wutil-go")
	if err := os.Chdir(root); err != nil {
		exitErr(err)
	}

	realCWD := callerCWD
	if envCWD := os.Getenv("WUTIL_REAL_CWD"); envCWD != "" {
		realCWD = envCWD
	}
	os.Setenv("WUTIL_ROOT", root)
	os.Setenv("WUTIL_REAL_CWD", realCWD)

	os.Setenv("WUTIL_DEBUG_MODE", debugMode)
	m, err := loadManifest(root, args)
	if err != nil {
		exitErr(err)
	}
	ctx := &Context{Root: root, RealCWD: realCWD, Manifest: m}
	if err := executeChain(ctx, args); err != nil {
		exitErr(err)
	}
	mark("Done!", true, "wutil-go")
}

func configureDebug(mode string) {
	if _, ok := debugModes[mode]; !ok {
		mode = "off"
	}
	debugMode = mode
	debugStart = time.Now()
	debugLast = debugStart
	if shouldShowDebug("log", true) {
		fmt.Printf("[debug:%s] [init] [wutil-go] timer started at %.4f\n", debugMode, float64(debugStart.UnixNano())/1e9)
	}
}

func shouldShowDebug(kind string, important bool) bool {
	settings := debugModes[debugMode]
	switch kind {
	case "mark":
		return settings.showMarks && (important || settings.verboseMarks)
	case "log":
		return settings.showLogs && (important || settings.verboseLogs)
	default:
		return false
	}
}

func debugLevel(important bool) string {
	if important {
		return "main"
	}
	return "detail"
}

func mark(label string, important bool, source string) {
	if debugStart.IsZero() {
		debugStart = time.Now()
		debugLast = debugStart
	}
	now := time.Now()
	total := now.Sub(debugStart).Seconds()
	sinceLast := now.Sub(debugLast).Seconds()
	debugLast = now
	if shouldShowDebug("mark", important) {
		fmt.Printf("[debug:%s] [mark:%s] [%s] %s | total %.3fs | +%.3fs\n", debugMode, debugLevel(important), source, label, total, sinceLast)
	}
}

func logDebug(message string, important bool, source string) {
	if !shouldShowDebug("log", important) {
		return
	}
	total := 0.0
	if !debugStart.IsZero() {
		total = time.Since(debugStart).Seconds()
	}
	fmt.Printf("[debug:%s] [log:%s] [%s] +%.3fs %s\n", debugMode, debugLevel(important), source, total, message)
}

func stripDebugFlags(raw []string) ([]string, string) {
	debugFlags := map[string]string{
		"--debug-lite":  "lite",
		"--debug-speed": "speed",
		"--debug":       "normal",
		"--debug-hard":  "hard",
	}
	mode := "off"
	args := make([]string, 0, len(raw))
	for _, arg := range raw {
		if value, ok := debugFlags[arg]; ok {
			mode = value
			continue
		}
		args = append(args, arg)
	}
	return args, mode
}

func findRoot() (string, error) {
	if root := os.Getenv("WUTIL_ROOT"); root != "" {
		return filepath.Abs(root)
	}

	cwd, _ := os.Getwd()
	if looksLikeRoot(cwd) {
		return filepath.Abs(cwd)
	}

	exe, err := os.Executable()
	if err == nil {
		dir := filepath.Dir(exe)
		if looksLikeRoot(dir) {
			return filepath.Abs(dir)
		}
		parent := filepath.Dir(dir)
		if looksLikeRoot(parent) {
			return filepath.Abs(parent)
		}
	}

	return "", errors.New("could not locate WindowUtil root; run from the install directory or set WUTIL_ROOT")
}

func looksLikeRoot(path string) bool {
	_, extErr := os.Stat(filepath.Join(path, "extensions"))
	_, runnerErr := os.Stat(filepath.Join(path, "python_runner.py"))
	return extErr == nil && runnerErr == nil
}

func loadManifest(root string, argv []string) (manifest, error) {
	mark("load manifest", false, "loader-go")
	m, err := readManifest(root)
	autoUpdate := readAutoUpdate(root)
	if err != nil || len(m) == 0 {
		logDebug("manifest missing or invalid; rebuilding synchronously", true, "loader-go")
		return rebuildManifest(root)
	}
	overlayGoCommands(m)
	if autoUpdate && !manifestResolves(m, argv) {
		logDebug("requested command not fully covered by cached manifest; refreshing synchronously", true, "loader-go")
		return rebuildManifest(root)
	}
	logDebug("manifest loaded from disk", false, "loader-go")
	return m, nil
}

func readManifest(root string) (manifest, error) {
	data, err := os.ReadFile(filepath.Join(root, "manifest.json"))
	if err != nil {
		return nil, err
	}
	var m manifest
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, err
	}
	return m, nil
}

func rebuildManifest(root string) (manifest, error) {
	mark("rebuild manifest", true, "loader-go")
	m := manifest{}
	entries, err := os.ReadDir(filepath.Join(root, "extensions"))
	if err != nil {
		return nil, err
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		if entry.Name() == "__init__.py" || entry.Name() == "__innit__.py" {
			continue
		}
		path := filepath.Join(root, "extensions", entry.Name())
		if strings.HasSuffix(entry.Name(), ".py") {
			logDebug(fmt.Sprintf("reading Python extension metadata from %s", entry.Name()), false, "loader-go")
			meta, ok := metadataFromPython(path, entry.Name())
			if ok {
				m[meta.name] = meta.entry
			}
		}
	}
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".go") {
			continue
		}
		path := filepath.Join(root, "extensions", entry.Name())
		{
			logDebug(fmt.Sprintf("reading Go extension metadata from %s", entry.Name()), false, "loader-go")
			meta, ok := metadataFromGo(path, entry.Name(), root)
			if ok {
				if err := buildGoExtension(root, entry.Name(), meta.name, meta.entry.Exe); err != nil {
					logDebug(fmt.Sprintf("failed to build Go extension %s: %s", entry.Name(), err), true, "loader-go")
					continue
				}
				m[meta.name] = meta.entry
			}
		}
	}
	overlayGoCommands(m)
	data, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return nil, err
	}
	if err := os.WriteFile(filepath.Join(root, "manifest.json"), data, 0644); err != nil {
		return nil, err
	}
	fmt.Printf("[windowutil] Auto-generated manifest with %d extensions.\n", len(m))
	logDebug(fmt.Sprintf("manifest contains %d commands", len(m)), true, "loader-go")
	mark("manifest rebuilt", true, "loader-go")
	return m, nil
}

func overlayGoCommands(m manifest) {
	for name, command := range goCommandRegistry {
		entry := command.Metadata()
		entry.Runtime = "go"
		entry.Handler = name
		m[name] = entry
	}
}

type pyMeta struct {
	name  string
	entry ManifestEntry
}

type goMeta struct {
	name  string
	entry ManifestEntry
}

func metadataFromPython(path, file string) (pyMeta, bool) {
	data, err := os.ReadFile(path)
	if err != nil {
		return pyMeta{}, false
	}
	source := string(data)
	if !strings.Contains(source, "class Extension") {
		return pyMeta{}, false
	}

	get := func(attr string) string {
		re := regexp.MustCompile(`(?m)^\s*self\.` + regexp.QuoteMeta(attr) + `\s*=\s*(.+?)\s*$`)
		match := re.FindStringSubmatch(source)
		if len(match) < 2 {
			return ""
		}
		return strings.TrimSpace(match[1])
	}

	name := literalString(get("name"))
	if name == "" {
		return pyMeta{}, false
	}
	args := literalStringList(get("args"))
	deps := literalStringList(get("deps"))
	requiresWindow := true
	if raw := get("requires_window"); raw != "" {
		requiresWindow = literalBool(raw, true)
	}
	short := literalString(get("short"))
	if short == "" {
		short = name
		if len(short) > 3 {
			short = short[:3]
		}
	}

	return pyMeta{
		name: name,
		entry: ManifestEntry{
			Args:           len(args),
			ArgNames:       args,
			Short:          short,
			Desc:           literalString(get("desc")),
			RequiresWindow: requiresWindow,
			File:           file,
			Deps:           deps,
			Runtime:        "python",
		},
	}, true
}

func metadataFromGo(path, file string, root string) (goMeta, bool) {
	data, err := os.ReadFile(path)
	if err != nil {
		return goMeta{}, false
	}
	values := map[string]string{}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "//wutil:") {
			continue
		}
		rest := strings.TrimSpace(strings.TrimPrefix(line, "//wutil:"))
		key, value, ok := strings.Cut(rest, " ")
		if !ok {
			continue
		}
		values[strings.TrimSpace(key)] = strings.TrimSpace(value)
	}
	name := values["name"]
	if name == "" {
		return goMeta{}, false
	}
	args := []string{}
	if raw := values["args"]; raw != "" {
		for _, part := range strings.Split(raw, ",") {
			part = strings.TrimSpace(part)
			if part != "" {
				args = append(args, part)
			}
		}
	}
	short := values["short"]
	if short == "" {
		short = name
		if len(short) > 3 {
			short = short[:3]
		}
	}
	exe := filepath.ToSlash(filepath.Join(".wutil", "goext", name+".exe"))
	return goMeta{
		name: name,
		entry: ManifestEntry{
			Args:           len(args),
			ArgNames:       args,
			Short:          short,
			Desc:           values["desc"],
			RequiresWindow: literalBool(values["requires_window"], false),
			File:           file,
			Exe:            exe,
			Runtime:        "go",
		},
	}, true
}

func buildGoExtension(root string, file string, name string, exeRel string) error {
	exePath := filepath.Join(root, filepath.FromSlash(exeRel))
	if err := os.MkdirAll(filepath.Dir(exePath), 0755); err != nil {
		return err
	}
	sourcePath := filepath.Join(root, "extensions", file)
	cmd := exec.Command("go", "build", "-o", exePath, sourcePath)
	cmd.Dir = root
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Env = os.Environ()
	return cmd.Run()
}

func literalString(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return ""
	}
	value, err := strconv.Unquote(raw)
	if err != nil {
		return ""
	}
	return value
}

func literalStringList(raw string) []string {
	raw = strings.TrimSpace(raw)
	if raw == "" || raw == "[]" {
		return []string{}
	}
	if !strings.HasPrefix(raw, "[") || !strings.HasSuffix(raw, "]") {
		return []string{}
	}
	inner := strings.TrimSpace(strings.TrimSuffix(strings.TrimPrefix(raw, "["), "]"))
	if inner == "" {
		return []string{}
	}
	parts := splitCSV(inner)
	values := []string{}
	for _, part := range parts {
		if value := literalString(strings.TrimSpace(part)); value != "" {
			values = append(values, value)
		}
	}
	return values
}

func splitCSV(value string) []string {
	var parts []string
	var current strings.Builder
	quote := rune(0)
	escaped := false
	for _, r := range value {
		if escaped {
			current.WriteRune(r)
			escaped = false
			continue
		}
		if r == '\\' {
			current.WriteRune(r)
			escaped = true
			continue
		}
		if quote != 0 {
			current.WriteRune(r)
			if r == quote {
				quote = 0
			}
			continue
		}
		if r == '\'' || r == '"' {
			quote = r
			current.WriteRune(r)
			continue
		}
		if r == ',' {
			parts = append(parts, current.String())
			current.Reset()
			continue
		}
		current.WriteRune(r)
	}
	parts = append(parts, current.String())
	return parts
}

func literalBool(raw string, fallback bool) bool {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "true":
		return true
	case "false":
		return false
	default:
		return fallback
	}
}

func manifestResolves(m manifest, argv []string) bool {
	if len(argv) == 0 {
		return true
	}
	for _, seg := range splitSegments(argv) {
		for i := 0; i < len(seg); {
			cmd, ok := resolveCommand(m, seg[i])
			if !ok {
				return false
			}
			i += 1 + argsNeeded(cmd)
		}
	}
	return true
}

func executeChain(ctx *Context, argv []string) error {
	mark("Start execute_chain", true, "wutil-go")
	logDebug(fmt.Sprintf("received argv=%v", argv), false, "wutil-go")
	for _, seg := range splitSegments(argv) {
		logDebug(fmt.Sprintf("processing segment=%v", seg), false, "wutil-go")
		for i := 0; i < len(seg); {
			name, entry, ok := resolveCommandName(ctx.Manifest, seg[i])
			if !ok {
				fmt.Printf("Unknown command: %s\n", seg[i])
				i++
				continue
			}
			needed := argsNeeded(entry)
			end := i + 1 + needed
			if end > len(seg) {
				end = len(seg)
			}
			cmdArgs := seg[i+1 : end]
			logDebug(fmt.Sprintf("resolved command=%s entry=%+v", name, entry), false, "wutil-go")
			logDebug(fmt.Sprintf("command args raw=%v", cmdArgs), false, "wutil-go")
			if err := runCommand(ctx, name, entry, cmdArgs); err != nil {
				return err
			}
			i += 1 + needed
		}
	}
	return nil
}

func splitSegments(argv []string) [][]string {
	var segments [][]string
	var current []string
	for _, arg := range argv {
		if strings.HasSuffix(arg, ",") || strings.HasSuffix(arg, ";") {
			current = append(current, strings.TrimSuffix(strings.TrimSuffix(arg, ","), ";"))
			segments = append(segments, current)
			current = nil
		} else if arg == "then" {
			segments = append(segments, current)
			current = nil
		} else {
			current = append(current, arg)
		}
	}
	if len(current) > 0 {
		segments = append(segments, current)
	}
	return segments
}

func resolveCommand(m manifest, token string) (ManifestEntry, bool) {
	_, entry, ok := resolveCommandName(m, token)
	return entry, ok
}

func resolveCommandName(m manifest, token string) (string, ManifestEntry, bool) {
	if entry, ok := m[token]; ok {
		return token, entry, true
	}
	for name, entry := range m {
		if entry.Short == token {
			return name, entry, true
		}
	}
	return "", ManifestEntry{}, false
}

func argsNeeded(entry ManifestEntry) int {
	if len(entry.ArgNames) > 0 {
		return len(entry.ArgNames)
	}
	return entry.Args
}

func runCommand(ctx *Context, name string, entry ManifestEntry, args []string) error {
	switch entry.Runtime {
	case "go":
		if entry.Handler != "" {
			return runGoCommand(ctx, entry.Handler, args)
		}
		return runGoExtensionCommand(ctx, name, entry, args)
	case "python", "":
		return runPythonCommand(ctx.Root, name, entry, args)
	default:
		return fmt.Errorf("unsupported runtime %q for command %q", entry.Runtime, name)
	}
}

func runGoExtensionCommand(ctx *Context, name string, entry ManifestEntry, args []string) error {
	mark(fmt.Sprintf("run Go extension %s", name), true, "wutil-go")
	if entry.Exe == "" {
		return fmt.Errorf("Go extension %q has no compiled exe; run `wutil install`", name)
	}
	exePath := filepath.Join(ctx.Root, filepath.FromSlash(entry.Exe))
	if _, err := os.Stat(exePath); err != nil {
		return fmt.Errorf("Go extension %q is not built at %s; run `wutil install`", name, exePath)
	}
	cmd := exec.Command(exePath, args...)
	cmd.Dir = ctx.Root
	cmd.Stdout = os.Stdout
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	cmd.Stdin = os.Stdin
	cmd.Env = os.Environ()
	if err := cmd.Run(); err != nil {
		message := strings.TrimSpace(stderr.String())
		if message == "" {
			message = err.Error()
		}
		return &CommandError{
			Title:   "WUTIL ERROR",
			Message: fmt.Sprintf("An error occurred in Go extension '%s':\n%s", name, message),
			Entry:   entry,
			Cause:   err,
		}
	}
	if stderr.Len() > 0 {
		fmt.Fprint(os.Stderr, stderr.String())
	}
	return nil
}

func runGoCommand(ctx *Context, handler string, args []string) error {
	mark(fmt.Sprintf("run Go command %s", handler), true, "wutil-go")
	command, ok := goCommandRegistry[handler]
	if !ok {
		return fmt.Errorf("unknown Go handler %q", handler)
	}
	return command.Run(ctx, args)
}

func runPythonCommand(root, name string, entry ManifestEntry, args []string) error {
	mark(fmt.Sprintf("run Python command %s", name), true, "wutil-go")
	python := filepath.Join(root, ".venv", "Scripts", "python.exe")
	if _, err := os.Stat(python); err != nil {
		return fmt.Errorf("Python compatibility runtime not found at %s; run `wutil install` from the WindowUtil root to bootstrap it", python)
	}
	runner := filepath.Join(root, "python_runner.py")
	if _, err := os.Stat(runner); err != nil {
		return fmt.Errorf("Python compatibility runner not found at %s", runner)
	}
	argNamesJSON, err := json.Marshal(entry.ArgNames)
	if err != nil {
		return err
	}

	cmdArgs := []string{
		runner,
		"--command", name,
		"--file", entry.File,
		"--requires-window", strconv.FormatBool(entry.RequiresWindow),
		"--arg-names", string(argNamesJSON),
		"--",
	}
	cmdArgs = append(cmdArgs, args...)
	cmd := exec.Command(python, cmdArgs...)
	cmd.Dir = root
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	cmd.Env = os.Environ()
	if err := cmd.Run(); err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			return nil
		}
		return err
	}
	return nil
}

type HelpCommand struct{}

func (HelpCommand) Metadata() ManifestEntry {
	return ManifestEntry{
		Args:           2,
		ArgNames:       []string{"command", "-lang"},
		Short:          "?",
		Desc:           "Lists all available commands, or details for a specific command.",
		RequiresWindow: false,
		Runtime:        "go",
		Handler:        "help",
	}
}

func (cmd HelpCommand) Run(ctx *Context, args []string) error {
	return commandHelp(ctx.Manifest, args)
}

type InstallCommand struct{}

func (InstallCommand) Metadata() ManifestEntry {
	return ManifestEntry{
		Args:           1,
		ArgNames:       []string{"auto-toggle"},
		Short:          "inst",
		Desc:           "Rebuild the mixed Go/Python manifest and optionally toggle auto-update.",
		RequiresWindow: false,
		Runtime:        "go",
		Handler:        "install",
	}
}

func (cmd InstallCommand) Run(ctx *Context, args []string) error {
	return commandInstall(ctx.Root, args)
}

func commandHelp(m manifest, args []string) error {
	command := ""
	showLang := false
	for _, arg := range args {
		if arg == "-lang" {
			showLang = true
			continue
		}
		if command == "" {
			command = arg
		}
	}
	if command != "" {
		name, entry, ok := resolveCommandName(m, command)
		if !ok {
			fmt.Println(styleMissing.Render(fmt.Sprintf("No command named '%s' found.", command)))
			return nil
		}
		fmt.Println(styleCommandHeader.Render(strings.ToUpper(name)))
		fmt.Println(styleShort.Render(fmt.Sprintf("Short: %s", entry.Short)))
		if showLang {
			fmt.Println(styleRuntime.Render(fmt.Sprintf("Runtime: %s", runtimeLabel(entry.Runtime))))
		}
		fmt.Printf("%s %s\n", styleDesc.Render("Description:"), entry.Desc)
		if len(entry.ArgNames) == 0 {
			fmt.Printf("%s None\n", styleArgs.Render("Arguments:"))
		} else {
			fmt.Printf("%s %s\n", styleArgs.Render("Arguments:"), strings.Join(entry.ArgNames, ", "))
		}
		return nil
	}

	fmt.Println(styleHelpHeader.Render("WindowUtil Command Reference"))
	fmt.Println()
	names := make([]string, 0, len(m))
	for name := range m {
		names = append(names, name)
	}
	sortStrings(names)
	for _, name := range names {
		entry := m[name]
		args := "None"
		if len(entry.ArgNames) > 0 {
			args = strings.Join(entry.ArgNames, ", ")
		}
		fmt.Printf("%s - %s", styleCommandName.Render(fmt.Sprintf("%-10s", name)), styleShort.Render(entry.Short))
		if showLang {
			fmt.Printf(" %s", styleRuntime.Render("["+runtimeLabel(entry.Runtime)+"]"))
		}
		fmt.Println()
		fmt.Println(styleDesc.Render("  " + entry.Desc))
		fmt.Println(styleArgs.Render("  Args: " + args))
		fmt.Println()
	}
	return nil
}

func runtimeLabel(runtime string) string {
	if runtime == "python" || runtime == "" {
		return "py"
	}
	return runtime
}

func commandInstall(root string, args []string) error {
	if _, err := rebuildManifest(root); err != nil {
		return err
	}
	fmt.Println("Manifest rebuilt.")
	if len(args) == 0 || strings.TrimSpace(args[0]) == "" {
		return nil
	}

	settingsPath := filepath.Join(root, "settings.json")
	settings := map[string]any{}
	if data, err := os.ReadFile(settingsPath); err == nil {
		_ = json.Unmarshal(data, &settings)
	}
	raw := strings.ToLower(strings.TrimSpace(args[0]))
	enable := map[string]bool{"enable": true, "-enable": true, "e": true, "-e": true, "on": true, "-on": true, "true": true}
	disable := map[string]bool{"disable": true, "-disable": true, "d": true, "-d": true, "off": true, "-off": true, "false": true}
	var next bool
	if enable[raw] {
		next = true
	} else if disable[raw] {
		next = false
	} else if current, ok := settings["auto-update"].(bool); ok {
		next = !current
	} else {
		next = true
	}
	settings["auto-update"] = next
	data, err := json.MarshalIndent(settings, "", "    ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(settingsPath, data, 0644); err != nil {
		return err
	}
	if next {
		fmt.Println("Auto-update has been enabled.")
	} else {
		fmt.Println("Auto-update has been disabled.")
	}
	return nil
}

func readAutoUpdate(root string) bool {
	data, err := os.ReadFile(filepath.Join(root, "settings.json"))
	if err != nil {
		return false
	}
	var settings map[string]any
	if json.Unmarshal(data, &settings) != nil {
		return false
	}
	value, ok := settings["auto-update"].(bool)
	return ok && value
}

func sortStrings(values []string) {
	for i := 1; i < len(values); i++ {
		for j := i; j > 0 && values[j] < values[j-1]; j-- {
			values[j], values[j-1] = values[j-1], values[j]
		}
	}
}

func exitErr(err error) {
	var commandErr *CommandError
	if errors.As(err, &commandErr) {
		printCoreError(commandErr.Title, commandErr.Message, commandErr.Entry, commandErr.Cause)
	} else {
		printCoreError("WUTIL ERROR", err.Error(), ManifestEntry{}, err)
	}
	os.Exit(1)
}

func printCoreError(title string, message string, entry ManifestEntry, cause error) {
	argsText := "No arguments"
	if len(entry.ArgNames) > 0 {
		argsText = strings.Join(entry.ArgNames, ", ")
	} else if entry.Args > 0 {
		argsText = fmt.Sprintf("%d positional argument(s)", entry.Args)
	}

	if debugMode == "off" || debugMode == "lite" {
		fmt.Printf("%s | %s\n", styleErrorTitle.Render(strings.ToUpper(title)), styleErrorLabel.Render("ERROR: "+strings.Join(strings.Fields(message), " ")))
		fmt.Println(styleErrorLabel.Render("Arguments: " + argsText))
		return
	}

	width := 70
	pad := (width - len(title) - 2) / 2
	if pad < 0 {
		pad = 0
	}
	fmt.Println()
	fmt.Println(styleErrorTitle.Render(strings.Repeat(" ", pad) + " " + strings.ToUpper(title) + " " + strings.Repeat(" ", pad)))
	fmt.Println()
	fmt.Println(styleErrorLabel.Render("Arguments: " + argsText))
	fmt.Println()
	fmt.Println(styleErrorLabel.Render("Error:"))
	fmt.Println(message)
	fmt.Println()
	if cause != nil {
		fmt.Println(styleTraceLabel.Render("Go Error"))
		fmt.Println(cause)
		fmt.Println()
	}
}
