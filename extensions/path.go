package main

//wutil:name path
//wutil:short p
//wutil:desc Manage WUtil executable aliases.
//wutil:args action,arg1,arg2
//wutil:requires_window false

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"windowutil/pkg/wutilext"
)

func main() {
	action, arg1, arg2 := "", "", ""
	if len(os.Args) > 1 {
		action = os.Args[1]
	}
	if len(os.Args) > 2 {
		arg1 = os.Args[2]
	}
	if len(os.Args) > 3 {
		arg2 = os.Args[3]
	}

	wutilext.Mark("path start", "path")
	wutilext.LogDetail(fmt.Sprintf("path action=%s arg1=%s arg2=%s", action, arg1, arg2), "path")

	switch action {
	case "add":
		add(arg1, arg2)
	case "delete":
		del(arg1)
	case "list":
		list()
	default:
		fmt.Println("Usage:")
		fmt.Println("  wutil path add <file> <alias>")
		fmt.Println("  wutil path delete <alias>")
		fmt.Println("  wutil path list")
	}
}

func add(file string, alias string) {
	if file == "" || alias == "" {
		fmt.Println("Usage: wutil path add <file> <alias>")
		wutilext.Log("path add aborted because file or alias was missing", "path")
		return
	}
	if !filepath.IsAbs(file) {
		file = filepath.Join(wutilext.RealCWD(), file)
	}
	file, _ = filepath.Abs(file)
	wutilext.LogDetail(fmt.Sprintf("resolved alias target path=%s", file), "path")
	if _, err := os.Stat(file); err != nil {
		fmt.Printf("Error: file not found: %s\n", file)
		wutilext.Log(fmt.Sprintf("path add failed because target was missing: %s", file), "path")
		return
	}

	paths := loadPaths()
	if _, exists := paths[alias]; exists {
		fmt.Printf("Alias '%s' already exists.\n", alias)
		wutilext.Log(fmt.Sprintf("path add rejected duplicate alias=%s", alias), "path")
		return
	}
	paths[alias] = file
	savePaths(paths)
	fmt.Printf("Added alias '%s' -> %s\n", alias, file)
	wutilext.Log(fmt.Sprintf("alias added alias=%s", alias), "path")
}

func del(alias string) {
	if alias == "" {
		fmt.Println("Usage: wutil path delete <alias>")
		wutilext.Log("path delete aborted because alias was missing", "path")
		return
	}
	paths := loadPaths()
	removed, exists := paths[alias]
	if !exists {
		fmt.Printf("Alias '%s' does not exist.\n", alias)
		wutilext.Log(fmt.Sprintf("path delete could not find alias=%s", alias), "path")
		return
	}
	delete(paths, alias)
	savePaths(paths)
	fmt.Printf("Deleted alias '%s' (was -> %s)\n", alias, removed)
	wutilext.Log(fmt.Sprintf("alias deleted alias=%s", alias), "path")
}

func list() {
	paths := loadPaths()
	if len(paths) == 0 {
		fmt.Println("No aliases stored.")
		wutilext.Log("path list found no aliases", "path")
		return
	}
	aliases := make([]string, 0, len(paths))
	for alias := range paths {
		aliases = append(aliases, alias)
	}
	sort.Strings(aliases)
	for _, alias := range aliases {
		fmt.Printf("%-12s -> %s\n", alias, paths[alias])
	}
	wutilext.Log(fmt.Sprintf("listed %d aliases", len(paths)), "path")
}

func loadPaths() map[string]string {
	data, err := os.ReadFile(pathFile())
	if err != nil {
		wutilext.LogDetail("paths.json does not exist yet", "path")
		return map[string]string{}
	}
	paths := map[string]string{}
	if err := json.Unmarshal(data, &paths); err != nil {
		wutilext.Log("failed to load alias paths; returning empty set", "path")
		return map[string]string{}
	}
	wutilext.LogDetail("loading alias paths from disk", "path")
	return paths
}

func savePaths(paths map[string]string) {
	file := pathFile()
	_ = os.MkdirAll(filepath.Dir(file), 0755)
	data, _ := json.MarshalIndent(paths, "", "    ")
	_ = os.WriteFile(file, data, 0644)
	wutilext.LogDetail(fmt.Sprintf("saving %d aliases", len(paths)), "path")
}

func pathFile() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".wutil", "paths.json")
}
