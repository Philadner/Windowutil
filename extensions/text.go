package main

//wutil:name text
//wutil:short txt
//wutil:desc An extension to output little tidbits of text that you use regularly.
//wutil:args id
//wutil:requires_window false

import (
	"fmt"
	"os"
	"path/filepath"

	"windowutil/pkg/wutilext"
)

func main() {
	id := "empty"
	if len(os.Args) > 1 {
		id = os.Args[1]
	}

	wutilext.Mark("text start", "text")
	home, err := os.UserHomeDir()
	if err != nil {
		fmt.Println("Text home directory not found.")
		wutilext.Log(fmt.Sprintf("text failed to resolve home directory: %s", err), "text")
		return
	}
	textPath := filepath.Join(home, ".wutil", "text", id+".txt")
	data, err := os.ReadFile(textPath)
	if err != nil {
		fmt.Printf("Text '%s' not found.\n", id)
		wutilext.Log(fmt.Sprintf("text not found. id=%s", id), "text")
		return
	}
	fmt.Print(string(data))
	if len(data) > 0 && data[len(data)-1] != '\n' {
		fmt.Println()
	}
	wutilext.Log(fmt.Sprintf("text outputted. id=%s", id), "text")
}
