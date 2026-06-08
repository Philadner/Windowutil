package main

//wutil:name state
//wutil:short s
//wutil:desc Save and restore groups of window positions.
//wutil:args action,subaction,target
//wutil:requires_window false

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"windowutil/pkg/wutilext"
	"windowutil/pkg/wutilwin"
)

type WindowPlacement struct {
	Title   string `json:"title"`
	ExeName string `json:"exe_name,omitempty"`
	ExePath string `json:"exe_path,omitempty"`
	Left    int    `json:"left"`
	Top     int    `json:"top"`
	Width   int    `json:"width"`
	Height  int    `json:"height"`
}

type WindowState struct {
	Name    string            `json:"name,omitempty"`
	Editing string            `json:"editing,omitempty"`
	Windows []WindowPlacement `json:"windows"`
}

func main() {
	action := ""
	subaction := ""
	target := ""
	if len(os.Args) > 1 {
		action = strings.ToLower(os.Args[1])
	}
	if len(os.Args) > 2 {
		subaction = os.Args[2]
		target = os.Args[2]
	}
	if len(os.Args) > 3 {
		target = os.Args[3]
	}

	wutilext.Mark("state start", "state")
	wutilext.LogDetail(fmt.Sprintf("state action=%s subaction=%s target=%s", action, subaction, target), "state")

	normalized := normalizeAction(action)
	if normalized == "states" {
		statesCommand(subaction, target)
		return
	}
	if normalized == "editor" {
		editorCommand(subaction)
		return
	}

	switch normalized {
	case "winadd":
		winAdd()
	case "winremove":
		winRemove()
	case "add":
		addByTitle(target)
	case "remove":
		removeByTitle(target)
	case "save":
		save(target)
	case "load":
		load(target)
	case "flush":
		flushBuilder()
	case "help":
		usage()
	default:
		usage()
	}
}

func normalizeAction(action string) string {
	switch action {
	case "winadd", "wadd", "w+", "win+":
		return "winadd"
	case "winremove", "wremove", "winrm", "wrm", "w-", "win-":
		return "winremove"
	case "add", "+":
		return "add"
	case "remove", "rm", "-":
		return "remove"
	case "save":
		return "save"
	case "load", "l":
		return "load"
	case "flush":
		return "flush"
	case "help", "?", "-h", "--help":
		return "help"
	case "states":
		return "states"
	case "editor":
		return "editor"
	default:
		return ""
	}
}

func statesCommand(action string, name string) {
	if strings.TrimSpace(action) == "" {
		fmt.Println("Usage: wutil state states <delete|edit|view> <name>")
		return
	}
	switch strings.ToLower(action) {
	case "delete", "del", "rm", "remove", "-":
		deleteState(name)
	case "edit":
		editState(name)
	case "view":
		viewState(name)
	default:
		fmt.Println("Usage: wutil state states <delete|edit|view> <name>")
	}
}

func editorCommand(action string) {
	if strings.TrimSpace(action) == "" {
		fmt.Println("Usage: wutil state editor view")
		return
	}
	switch strings.ToLower(action) {
	case "view":
		viewEditor()
	default:
		fmt.Println("Usage: wutil state editor view")
	}
}

func winAdd() {
	win, err := wutilwin.RequireSelected("state")
	if err != nil {
		fmt.Println(err)
		return
	}
	placement, err := placementFromWindow(*win)
	if err != nil {
		fmt.Println("Window is no longer valid (likely closed).")
		return
	}
	builder := readState(builderPath())
	upsert(&builder, placement)
	writeState(builderPath(), builder)
	fmt.Printf("Added '%s' to state builder.\n", placement.Title)
	wutilext.Log(fmt.Sprintf("builder added selected window=%s", placement.Title), "state")
}

func winRemove() {
	win, err := wutilwin.RequireSelected("state")
	if err != nil {
		fmt.Println(err)
		return
	}
	placement, err := placementFromWindow(*win)
	if err != nil {
		fmt.Println("Window is no longer valid (likely closed).")
		return
	}
	removePlacement(placement)
}

func addByTitle(title string) {
	if strings.TrimSpace(title) == "" {
		fmt.Println("Usage: wutil state add <window>")
		return
	}
	win, ok := chooseWindow(title)
	if !ok {
		return
	}
	placement, err := placementFromWindow(win)
	if err != nil {
		fmt.Println("Window is no longer valid (likely closed).")
		return
	}
	builder := readState(builderPath())
	upsert(&builder, placement)
	writeState(builderPath(), builder)
	fmt.Printf("Added '%s' to state builder.\n", placement.Title)
	wutilext.Log(fmt.Sprintf("builder added window=%s", placement.Title), "state")
}

func removeByTitle(title string) {
	if strings.TrimSpace(title) == "" {
		fmt.Println("Usage: wutil state remove <window>")
		return
	}
	win, ok := chooseWindow(title)
	if !ok {
		return
	}
	placement, err := placementFromWindow(win)
	if err != nil {
		fmt.Println("Window is no longer valid (likely closed).")
		return
	}
	removePlacement(placement)
}

func removePlacement(reference WindowPlacement) {
	builder := readState(builderPath())
	next := make([]WindowPlacement, 0, len(builder.Windows))
	removed := false
	for _, placement := range builder.Windows {
		if samePlacementIdentity(placement, reference) {
			removed = true
			continue
		}
		next = append(next, placement)
	}
	builder.Windows = next
	writeState(builderPath(), builder)
	if removed {
		fmt.Printf("Removed '%s' from state builder.\n", reference.Title)
		wutilext.Log(fmt.Sprintf("builder removed window=%s", reference.Title), "state")
	} else {
		fmt.Printf("'%s' was not in the state builder.\n", reference.Title)
	}
}

func save(name string) {
	builder := readState(builderPath())
	name = strings.TrimSpace(name)
	if name == "" && builder.Editing != "" {
		name = builder.Editing
	}
	if name == "" {
		fmt.Println("Usage: wutil state save <name>")
		return
	}
	if len(builder.Windows) == 0 {
		fmt.Println("State builder is empty.")
		return
	}
	wasEditing := builder.Editing
	builder.Name = name
	builder.Editing = ""
	path := statePath(name)
	writeState(path, builder)
	fmt.Printf("Saved state '%s' with %d window(s).\n", name, len(builder.Windows))
	if wasEditing != "" {
		fmt.Printf("Finished editing '%s'.\n", wasEditing)
	}
	clearBuilder()
	wutilext.Log(fmt.Sprintf("saved state=%s windows=%d", name, len(builder.Windows)), "state")
}

func load(name string) {
	if strings.TrimSpace(name) == "" {
		fmt.Println("Usage: wutil state load <name>")
		return
	}
	state := readState(statePath(name))
	if len(state.Windows) == 0 {
		fmt.Printf("State '%s' not found or empty.\n", name)
		return
	}

	var wait sync.WaitGroup
	for _, placement := range state.Windows {
		win, ok := resolveSavedWindow(placement)
		if !ok {
			fmt.Printf("Window not found for saved title '%s'.\n", placement.Title)
			wutilext.Log(fmt.Sprintf("load missing window=%s", placement.Title), "state")
			continue
		}
		wait.Add(1)
		go func() {
			defer wait.Done()
			animateTo(win, placement)
		}()
	}
	wait.Wait()
	fmt.Printf("Loaded state '%s'.\n", name)
	wutilext.Log(fmt.Sprintf("loaded state=%s", name), "state")
}

func flushBuilder() {
	clearBuilder()
	fmt.Println("State builder flushed.")
	wutilext.Log("builder flushed", "state")
}

func deleteState(name string) {
	if strings.TrimSpace(name) == "" {
		fmt.Println("Usage: wutil state states delete <name>")
		return
	}
	path := statePath(name)
	if _, err := os.Stat(path); err != nil {
		fmt.Printf("State '%s' not found.\n", name)
		return
	}
	if err := os.Remove(path); err != nil {
		fmt.Printf("Could not delete state '%s': %s\n", name, err)
		return
	}
	builder := readState(builderPath())
	if strings.EqualFold(builder.Editing, cleanStateName(name)) {
		clearBuilder()
	}
	fmt.Printf("Deleted state '%s'.\n", cleanStateName(name))
	wutilext.Log(fmt.Sprintf("deleted state=%s", cleanStateName(name)), "state")
}

func editState(name string) {
	if strings.TrimSpace(name) == "" {
		fmt.Println("Usage: wutil state states edit <name>")
		return
	}
	state := readState(statePath(name))
	if len(state.Windows) == 0 {
		fmt.Printf("State '%s' not found or empty.\n", name)
		return
	}
	state.Name = cleanStateName(name)
	state.Editing = cleanStateName(name)
	writeState(builderPath(), state)
	fmt.Printf("Opened state '%s' in the editor with %d window(s).\n", state.Name, len(state.Windows))
	wutilext.Log(fmt.Sprintf("editing state=%s windows=%d", state.Name, len(state.Windows)), "state")
}

func viewEditor() {
	builder := readState(builderPath())
	if len(builder.Windows) == 0 {
		fmt.Println("State editor is empty.")
		return
	}
	name := "builder"
	if builder.Editing != "" {
		name = "editing " + builder.Editing
	}
	printStateWindows(name, builder)
}

func viewState(name string) {
	if strings.TrimSpace(name) == "" {
		fmt.Println("Usage: wutil state states view <name>")
		return
	}
	state := readState(statePath(name))
	if len(state.Windows) == 0 {
		fmt.Printf("State '%s' not found or empty.\n", name)
		return
	}
	printStateWindows(cleanStateName(name), state)
}

func printStateWindows(label string, state WindowState) {
	fmt.Printf("%s: %d window(s)\n", label, len(state.Windows))
	for index, placement := range state.Windows {
		exe := placement.ExeName
		if exe == "" {
			exe = filepath.Base(placement.ExePath)
		}
		if exe == "." {
			exe = "unknown exe"
		}
		fmt.Printf("[%d] %s\n", index, placement.Title)
		fmt.Printf("    exe: %s\n", exe)
		fmt.Printf("    pos: %d,%d size: %dx%d\n", placement.Left, placement.Top, placement.Width, placement.Height)
	}
}

func placementFromWindow(win wutilwin.Window) (WindowPlacement, error) {
	bounds, err := win.Bounds()
	if err != nil {
		return WindowPlacement{}, err
	}
	return WindowPlacement{
		Title:   win.Title(),
		ExeName: win.ExeName(),
		ExePath: win.ExePath(),
		Left:    bounds.Left,
		Top:     bounds.Top,
		Width:   bounds.Width,
		Height:  bounds.Height,
	}, nil
}

func resolveSavedWindow(placement WindowPlacement) (wutilwin.Window, bool) {
	all, err := wutilwin.All()
	if err != nil {
		return wutilwin.Window{}, false
	}

	for _, win := range all {
		if strings.EqualFold(win.Title(), placement.Title) {
			if placement.ExeName == "" || sameExe(win, placement) {
				wutilext.LogDetail(fmt.Sprintf("matched exact title=%s", placement.Title), "state")
				return win, true
			}
		}
	}

	exeCandidates := []wutilwin.Window{}
	if placement.ExeName != "" || placement.ExePath != "" {
		for _, win := range all {
			if sameExe(win, placement) {
				exeCandidates = append(exeCandidates, win)
			}
		}
	}
	if len(exeCandidates) > 0 {
		win, score := nearestByTitle(exeCandidates, placement.Title)
		wutilext.Log(fmt.Sprintf("matched saved window by exe=%s nearest_title=%q score=%d", placement.ExeName, win.Title(), score), "state")
		return win, true
	}

	win, score := nearestByTitle(all, placement.Title)
	if score > 0 {
		wutilext.Log(fmt.Sprintf("matched saved window by nearest_title=%q score=%d", win.Title(), score), "state")
		return win, true
	}
	return wutilwin.Window{}, false
}

func sameExe(win wutilwin.Window, placement WindowPlacement) bool {
	if placement.ExePath != "" && strings.EqualFold(win.ExePath(), placement.ExePath) {
		return true
	}
	if placement.ExeName != "" && strings.EqualFold(win.ExeName(), placement.ExeName) {
		return true
	}
	return false
}

func nearestByTitle(windows []wutilwin.Window, savedTitle string) (wutilwin.Window, int) {
	bestScore := -1
	var best wutilwin.Window
	for _, win := range windows {
		score := titleScore(savedTitle, win.Title())
		if score > bestScore {
			bestScore = score
			best = win
		}
	}
	return best, bestScore
}

func titleScore(saved string, candidate string) int {
	saved = strings.ToLower(saved)
	candidate = strings.ToLower(candidate)
	if saved == candidate {
		return 100000
	}
	if strings.Contains(candidate, saved) || strings.Contains(saved, candidate) {
		return 50000 + min(len(saved), len(candidate))
	}

	savedTokens := titleTokens(saved)
	candidateTokens := map[string]bool{}
	for _, token := range titleTokens(candidate) {
		candidateTokens[token] = true
	}
	score := 0
	for _, token := range savedTokens {
		if candidateTokens[token] {
			score += len(token) * 10
		}
	}
	score -= levenshtein(saved, candidate)
	return score
}

func titleTokens(title string) []string {
	fields := strings.FieldsFunc(title, func(r rune) bool {
		return !(r >= 'a' && r <= 'z' || r >= '0' && r <= '9')
	})
	tokens := []string{}
	for _, field := range fields {
		if len(field) > 1 {
			tokens = append(tokens, field)
		}
	}
	return tokens
}

func levenshtein(a string, b string) int {
	if len(a) == 0 {
		return len(b)
	}
	if len(b) == 0 {
		return len(a)
	}
	prev := make([]int, len(b)+1)
	curr := make([]int, len(b)+1)
	for j := range prev {
		prev[j] = j
	}
	for i := 1; i <= len(a); i++ {
		curr[0] = i
		for j := 1; j <= len(b); j++ {
			cost := 0
			if a[i-1] != b[j-1] {
				cost = 1
			}
			curr[j] = min(curr[j-1]+1, min(prev[j]+1, prev[j-1]+cost))
		}
		prev, curr = curr, prev
	}
	return prev[len(b)]
}

func min(a int, b int) int {
	if a < b {
		return a
	}
	return b
}

func chooseWindow(title string) (wutilwin.Window, bool) {
	matches, err := wutilwin.FindByTitle(title)
	if err != nil {
		fmt.Printf("An error occurred: %s\n", err)
		return wutilwin.Window{}, false
	}
	if len(matches) == 0 {
		fmt.Printf("No window found containing '%s'.\n", title)
		return wutilwin.Window{}, false
	}
	if len(matches) == 1 {
		return matches[0], true
	}

	fmt.Printf("Multiple matches for '%s':\n", title)
	for i, match := range matches {
		fmt.Printf("[%d] %s\n", i, match.Title())
	}
	fmt.Print("Select index: ")
	line, _ := bufio.NewReader(os.Stdin).ReadString('\n')
	index, err := strconv.Atoi(strings.TrimSpace(line))
	if err != nil || index < 0 || index >= len(matches) {
		fmt.Println("Invalid choice.")
		return wutilwin.Window{}, false
	}
	return matches[index], true
}

func upsert(state *WindowState, placement WindowPlacement) {
	for i, existing := range state.Windows {
		if samePlacementIdentity(existing, placement) {
			state.Windows[i] = placement
			return
		}
	}
	state.Windows = append(state.Windows, placement)
}

func samePlacementIdentity(a WindowPlacement, b WindowPlacement) bool {
	if strings.EqualFold(a.Title, b.Title) {
		return true
	}
	if a.ExePath != "" && b.ExePath != "" && strings.EqualFold(a.ExePath, b.ExePath) {
		return true
	}
	if a.ExeName != "" && b.ExeName != "" && strings.EqualFold(a.ExeName, b.ExeName) {
		return true
	}
	return false
}

func animateTo(win wutilwin.Window, placement WindowPlacement) {
	start, err := win.Bounds()
	if err != nil {
		return
	}
	steps := 18
	sleep := 12 * time.Millisecond
	for i := 1; i <= steps; i++ {
		t := float64(i) / float64(steps)
		eased := t * t * (3 - 2*t)
		left := start.Left + int(float64(placement.Left-start.Left)*eased)
		top := start.Top + int(float64(placement.Top-start.Top)*eased)
		width := start.Width + int(float64(placement.Width-start.Width)*eased)
		height := start.Height + int(float64(placement.Height-start.Height)*eased)
		_ = win.MoveResize(left, top, width, height)
		time.Sleep(sleep)
	}
	_ = win.MoveResize(placement.Left, placement.Top, placement.Width, placement.Height)
}

func readState(path string) WindowState {
	data, err := os.ReadFile(path)
	if err != nil {
		return WindowState{Windows: []WindowPlacement{}}
	}
	var state WindowState
	if err := json.Unmarshal(data, &state); err != nil {
		return WindowState{Windows: []WindowPlacement{}}
	}
	if state.Windows == nil {
		state.Windows = []WindowPlacement{}
	}
	return state
}

func writeState(path string, state WindowState) {
	_ = os.MkdirAll(filepath.Dir(path), 0755)
	data, _ := json.MarshalIndent(state, "", "  ")
	_ = os.WriteFile(path, data, 0644)
}

func clearBuilder() {
	_ = os.Remove(builderPath())
}

func builderPath() string {
	return filepath.Join(statesDir(), "_builder.json")
}

func statePath(name string) string {
	name = cleanStateName(name)
	return filepath.Join(statesDir(), name+".json")
}

func cleanStateName(name string) string {
	return strings.TrimSuffix(filepath.Base(strings.TrimSpace(name)), ".json")
}

func statesDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return filepath.Join(wutilext.Root(), ".wutil", "states")
	}
	return filepath.Join(home, ".wutil", "states")
}

func usage() {
	fmt.Println("State commands:")
	fmt.Println("  s winadd                  add the selected window to the builder")
	fmt.Println("  s winremove               remove the selected window from the builder")
	fmt.Println("  s add <window>            add a matching window to the builder")
	fmt.Println("  s remove <window>         remove a matching window from the builder")
	fmt.Println("  s save [name]             save the builder; name is optional while editing")
	fmt.Println("  s load <name>             restore a saved state with animation")
	fmt.Println("  s flush                   clear the builder/editor")
	fmt.Println("  s editor view             show the current builder/editor windows")
	fmt.Println("  s states view <name>      show a saved state's windows")
	fmt.Println("  s states edit <name>      open a saved state in the editor")
	fmt.Println("  s states delete <name>    delete a saved state")
	fmt.Println("")
	fmt.Println("Aliases:")
	fmt.Println("  state=s, help=?")
	fmt.Println("  load=l")
	fmt.Println("  winadd=wadd,w+,win+")
	fmt.Println("  winremove=wremove,winrm,wrm,w-,win-")
	fmt.Println("  add=+, remove=rm,-")
	fmt.Println("  states delete=states del,states rm,states -")
}
