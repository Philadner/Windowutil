package main

//wutil:name centre
//wutil:short cen
//wutil:desc Center a window on the screen, with optional nudge or animation.
//wutil:args widthnudge,heightnudge,animated
//wutil:requires_window true

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"windowutil/pkg/wutilext"
	"windowutil/pkg/wutilwin"
)

func main() {
	widthNudge := intArg(1, 0)
	heightNudge := intArg(2, 0)
	animated := boolArg(3, true)
	wutilext.Mark("centre start", "centre")
	wutilext.LogDetail(fmt.Sprintf("requested centre widthnudge=%d heightnudge=%d animated=%v", widthNudge, heightNudge, animated), "centre")

	win, err := wutilwin.RequireSelected("centre")
	if err != nil {
		fmt.Println(err)
		return
	}
	bounds, err := win.Bounds()
	if err != nil {
		fmt.Println("Window is no longer valid (likely closed).")
		wutilext.Log("window handle became invalid during centre", "centre")
		return
	}
	screenWidth, screenHeight := wutilwin.ScreenSize()
	wutilext.LogDetail(fmt.Sprintf("screen size=%dx%d current size=%dx%d", screenWidth, screenHeight, bounds.Width, bounds.Height), "centre")
	targetX := (screenWidth-bounds.Width)/2 + widthNudge
	targetY := (screenHeight-bounds.Height)/2 + heightNudge
	if animated {
		wutilext.Log("using animated move", "centre")
		animateMove(*win, bounds.Left, bounds.Top, targetX, targetY, 400*time.Millisecond, 40)
	} else {
		wutilext.LogDetail("using direct move", "centre")
		_ = win.MoveTo(targetX, targetY)
	}
	fmt.Printf("Window '%s' centered at (%d, %d).\n", win.Title(), targetX, targetY)
	wutilext.Mark("centre complete", "centre")
}

func animateMove(win wutilwin.Window, fromX int, fromY int, toX int, toY int, duration time.Duration, steps int) {
	if steps <= 0 {
		_ = win.MoveTo(toX, toY)
		return
	}
	sleep := duration / time.Duration(steps)
	for i := 1; i <= steps; i++ {
		t := float64(i) / float64(steps)
		eased := t * t * (3 - 2*t)
		x := fromX + int(float64(toX-fromX)*eased)
		y := fromY + int(float64(toY-fromY)*eased)
		_ = win.MoveTo(x, y)
		time.Sleep(sleep)
	}
}

func intArg(index int, fallback int) int {
	if len(os.Args) <= index {
		return fallback
	}
	value, err := strconv.Atoi(os.Args[index])
	if err != nil {
		return fallback
	}
	return value
}

func boolArg(index int, fallback bool) bool {
	if len(os.Args) <= index {
		return fallback
	}
	switch strings.ToLower(os.Args[index]) {
	case "true", "1", "yes", "y", "on":
		return true
	case "false", "0", "no", "n", "off":
		return false
	default:
		return fallback
	}
}
