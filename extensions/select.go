package main

//wutil:name select
//wutil:short sel
//wutil:desc Select a window by fuzzy title match.
//wutil:args search_term
//wutil:requires_window false

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"windowutil/pkg/wutilext"
	"windowutil/pkg/wutilwin"
)

func main() {
	search := ""
	if len(os.Args) > 1 {
		search = os.Args[1]
	}
	wutilext.Mark("select start", "select")
	wutilext.Log(fmt.Sprintf("searching for window term=%s", search), "select")

	all, _ := wutilwin.All()
	matches, err := wutilwin.FindByTitle(search)
	if err != nil {
		fmt.Printf("An error occurred: %s\n", err)
		wutilext.Log(fmt.Sprintf("select failed: %s", err), "select")
		return
	}
	wutilext.LogDetail(fmt.Sprintf("window candidates total=%d matches=%d", len(all), len(matches)), "select")
	if len(matches) == 0 {
		fmt.Printf("No window found containing '%s'.\n", search)
		wutilext.Log("select found no matches", "select")
		return
	}

	win := matches[0]
	if len(matches) > 1 {
		fmt.Printf("Multiple matches for '%s':\n", search)
		for i, match := range matches {
			fmt.Printf("[%d] %s\n", i, match.Title())
		}
		fmt.Print("Select index: ")
		line, _ := bufio.NewReader(os.Stdin).ReadString('\n')
		index, err := strconv.Atoi(strings.TrimSpace(line))
		if err != nil || index < 0 || index >= len(matches) {
			fmt.Println("Invalid choice.")
			wutilext.Log("select received invalid interactive choice", "select")
			return
		}
		win = matches[index]
	}

	if err := wutilwin.SaveSelected(win); err != nil {
		fmt.Printf("Failed to save selected window: %s\n", err)
		return
	}
	fmt.Printf("Selected window: '%s'\n", win.Title())
	wutilext.Log(fmt.Sprintf("selected window title=%s", win.Title()), "select")
	wutilext.Mark("select complete", "select")
}
