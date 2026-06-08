package main

//wutil:name resize
//wutil:short res
//wutil:desc Resize windows smoothly by side, axis, or all sides equally.
//wutil:args side,amount
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
	side := ""
	if len(os.Args) > 1 {
		side = strings.ToLower(os.Args[1])
	}
	amount, hasAmount := optionalInt(2)
	wutilext.Mark("resize start", "resize")
	wutilext.LogDetail(fmt.Sprintf("requested resize side=%s amount=%v", side, maybeInt(amount, hasAmount)), "resize")

	win, err := wutilwin.RequireSelected("resize")
	if err != nil {
		fmt.Println(err)
		return
	}
	direction := resolveDirection(side)
	if direction == "" {
		if side == "" {
			fmt.Println("Missing required argument: side")
		} else {
			fmt.Printf("Unknown side '%s'\n", side)
		}
		wutilext.Log(fmt.Sprintf("resize direction could not be resolved from side=%s", side), "resize")
		return
	}
	if hasAmount {
		wutilext.Log(fmt.Sprintf("running one-off resize direction=%s delta=%d", direction, amount), "resize")
		resizeOnce(*win, direction, amount)
	} else {
		fmt.Printf("Interactive resize mode (%s). Use arrow keys, ESC to exit.\n", direction)
		wutilext.Log(fmt.Sprintf("starting interactive resize direction=%s", direction), "resize")
		interactiveResize(*win, direction)
	}
	wutilext.Mark("resize complete", "resize")
}

func resolveDirection(side string) string {
	aliases := map[string]string{
		"left": "left", "l": "left",
		"right": "right", "r": "right",
		"top": "top", "up": "top", "u": "top",
		"bottom": "bottom", "down": "bottom", "d": "bottom",
		"all": "all", "equal": "all", "eq": "all",
		"horizontal": "horizontal", "hor": "horizontal", "x": "horizontal",
		"vertical": "vertical", "ver": "vertical", "vert": "vertical", "y": "vertical",
	}
	return aliases[side]
}

func resizeOnce(win wutilwin.Window, direction string, delta int) {
	bounds, err := win.Bounds()
	if err != nil {
		fmt.Println("Window is no longer valid (likely closed).")
		wutilext.Log("window handle became invalid during resize", "resize")
		return
	}
	left, top, width, height := resized(bounds, direction, delta)
	animateMoveResize(win, bounds, left, top, width, height, 150*time.Millisecond, 15)
	wutilext.Log(fmt.Sprintf("_resize_once applied left=%d top=%d width=%d height=%d", left, top, width, height), "resize")
}

func interactiveResize(win wutilwin.Window, direction string) {
	for {
		if wutilwin.EscapePressed() {
			fmt.Println("Exiting resize mode.")
			wutilext.Log("interactive resize stopped by esc", "resize")
			return
		}
		delta := 0
		if wutilwin.RightPressed() || wutilwin.UpPressed() {
			delta = 10
		}
		if wutilwin.LeftPressed() || wutilwin.DownPressed() {
			delta = -10
		}
		if delta != 0 {
			bounds, err := win.Bounds()
			if err == nil {
				left, top, width, height := resized(bounds, direction, delta)
				_ = win.MoveResize(left, top, width, height)
				wutilext.LogDetail(fmt.Sprintf("interactive resize target left=%d top=%d width=%d height=%d", left, top, width, height), "resize")
			}
			time.Sleep(50 * time.Millisecond)
		}
		time.Sleep(10 * time.Millisecond)
	}
}

func resized(bounds wutilwin.Bounds, direction string, delta int) (int, int, int, int) {
	left, top, width, height := bounds.Left, bounds.Top, bounds.Width, bounds.Height
	switch direction {
	case "left":
		left -= delta
		width += delta
	case "right":
		width += delta
	case "top":
		top -= delta
		height += delta
	case "bottom":
		height += delta
	case "horizontal":
		left -= delta / 2
		width += delta
	case "vertical":
		top -= delta / 2
		height += delta
	case "all":
		left -= delta / 2
		top -= delta / 2
		width += delta
		height += delta
	}
	if width < 50 {
		width = 50
	}
	if height < 50 {
		height = 50
	}
	return left, top, width, height
}

func animateMoveResize(win wutilwin.Window, from wutilwin.Bounds, left int, top int, width int, height int, duration time.Duration, steps int) {
	if steps <= 0 {
		_ = win.MoveResize(left, top, width, height)
		return
	}
	sleep := duration / time.Duration(steps)
	for i := 1; i <= steps; i++ {
		t := float64(i) / float64(steps)
		x := from.Left + int(float64(left-from.Left)*t)
		y := from.Top + int(float64(top-from.Top)*t)
		w := from.Width + int(float64(width-from.Width)*t)
		h := from.Height + int(float64(height-from.Height)*t)
		_ = win.MoveResize(x, y, w, h)
		time.Sleep(sleep)
	}
}

func optionalInt(index int) (int, bool) {
	if len(os.Args) <= index {
		return 0, false
	}
	value, err := strconv.Atoi(os.Args[index])
	if err != nil {
		return 0, false
	}
	return value, true
}

func maybeInt(value int, ok bool) any {
	if !ok {
		return nil
	}
	return value
}
