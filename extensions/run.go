package main

//wutil:name run
//wutil:short r
//wutil:desc Run an alias created with wutil path.
//wutil:args alias,args
//wutil:requires_window false

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"windowutil/pkg/wutilext"
)

func main() {
	alias, extraArgs := "", ""
	if len(os.Args) > 1 {
		alias = os.Args[1]
	}
	if len(os.Args) > 2 {
		extraArgs = os.Args[2]
	}

	wutilext.Mark("run start", "run")
	wutilext.LogDetail(fmt.Sprintf("run requested alias=%s args=%s", alias, extraArgs), "run")
	if alias == "" {
		fmt.Println("Alias '' not found.")
		return
	}

	paths := loadPaths()
	target, ok := paths[alias]
	if !ok {
		fmt.Printf("Alias '%s' not found.\n", alias)
		wutilext.Log(fmt.Sprintf("run failed because alias=%s was missing", alias), "run")
		return
	}
	if _, err := os.Stat(target); err != nil {
		fmt.Printf("Stored file no longer exists: %s\n", target)
		wutilext.Log(fmt.Sprintf("run failed because target path was missing: %s", target), "run")
		return
	}

	argList := []string{}
	if strings.TrimSpace(extraArgs) != "" {
		argList = strings.Split(extraArgs, " ")
	}
	runExe := target
	runArgs := argList
	if strings.EqualFold(filepath.Ext(target), ".py") {
		runExe = filepath.Join(wutilext.Root(), ".venv", "Scripts", "python.exe")
		runArgs = append([]string{target}, argList...)
	}

	cmd := exec.Command(runExe, runArgs...)
	cmd.Dir = filepath.Dir(target)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	cmd.Env = os.Environ()
	wutilext.Log(fmt.Sprintf("launching command=%v cwd=%s", append([]string{runExe}, runArgs...), cmd.Dir), "run")
	if err := cmd.Run(); err != nil {
		fmt.Printf("Failed to run alias: %s\n", err)
		wutilext.Log(fmt.Sprintf("run failed for alias=%s: %s", alias, err), "run")
	}
}

func loadPaths() map[string]string {
	home, _ := os.UserHomeDir()
	data, err := os.ReadFile(filepath.Join(home, ".wutil", "paths.json"))
	if err != nil {
		wutilext.LogDetail("run could not find paths.json", "run")
		return map[string]string{}
	}
	paths := map[string]string{}
	if err := json.Unmarshal(data, &paths); err != nil {
		wutilext.Log("run failed to decode aliases file", "run")
		return map[string]string{}
	}
	wutilext.LogDetail("run loaded aliases from disk", "run")
	return paths
}
