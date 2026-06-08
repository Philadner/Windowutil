package main

//wutil:name gofail
//wutil:short gof
//wutil:desc A Go extension that always fails.
//wutil:args reason
//wutil:requires_window false

import (
	"fmt"
	"os"

	"windowutil/pkg/wutilext"
)

func main() {
	reason := "intentional test failure"
	if len(os.Args) > 1 {
		reason = os.Args[1]
	}
	wutilext.Mark("gofail start", "gofail")
	wutilext.Log(fmt.Sprintf("gofail about to fail reason=%s", reason), "gofail")
	fmt.Fprintf(os.Stderr, "gofail exploded: %s\n", reason)
	os.Exit(1)
}
