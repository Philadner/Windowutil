package main

//wutil:name nudge
//wutil:short nud
//wutil:desc Smooth queued nudge with diagonal support.
//wutil:args widthnudge,heightnudge
//wutil:requires_window true

import (
	"fmt"
	"math"
	"os"
	"strconv"
	"sync"
	"time"

	"windowutil/pkg/wutilext"
	"windowutil/pkg/wutilwin"
)

func main() {
	wutilext.Mark("nudge start", "nudge")
	width, hasWidth := optionalInt(1)
	height, hasHeight := optionalInt(2)
	wutilext.LogDetail(fmt.Sprintf("requested nudge width=%v height=%v", maybeInt(width, hasWidth), maybeInt(height, hasHeight)), "nudge")

	win, err := wutilwin.RequireSelected("nudge")
	if err != nil {
		fmt.Println(err)
		return
	}
	bounds, err := win.Bounds()
	if err != nil {
		fmt.Println("Window is no longer valid (likely closed).")
		wutilext.Log("window handle became invalid during nudge", "nudge")
		return
	}

	if hasWidth && hasHeight {
		newLeft := bounds.Left + width
		newTop := bounds.Top + height
		wutilext.Log(fmt.Sprintf("one-off move target=(%d, %d)", newLeft, newTop), "nudge")
		_ = win.MoveTo(newLeft, newTop)
		fmt.Printf("Window '%s' nudged to (%d, %d).\n", win.Title(), newLeft, newTop)
		wutilext.Mark("nudge complete", "nudge")
		return
	}

	fmt.Println("Queued nudge mode (diagonal). Use arrow keys; ESC to stop.")
	interactiveNudge(*win, bounds)
}

func interactiveNudge(win wutilwin.Window, start wutilwin.Bounds) {
	targetX := float64(start.Left)
	targetY := float64(start.Top)
	stop := false
	var lock sync.Mutex

	go func() {
		for {
			lock.Lock()
			if stop {
				lock.Unlock()
				return
			}
			x, y := targetX, targetY
			lock.Unlock()

			bounds, err := win.Bounds()
			if err == nil {
				dx := x - float64(bounds.Left)
				dy := y - float64(bounds.Top)
				if math.Abs(dx) >= 1 || math.Abs(dy) >= 1 {
					_ = win.MoveTo(bounds.Left+int(dx*0.4), bounds.Top+int(dy*0.4))
					wutilext.LogDetail(fmt.Sprintf("animating toward (%.1f, %.1f)", x, y), "nudge")
				}
			}
			time.Sleep(10 * time.Millisecond)
		}
	}()

	for {
		if wutilwin.EscapePressed() {
			lock.Lock()
			stop = true
			lock.Unlock()
			fmt.Println("Exiting nudge mode.")
			wutilext.Log("interactive nudge stopped by esc", "nudge")
			return
		}
		dx := 0
		dy := 0
		if wutilwin.RightPressed() {
			dx++
		}
		if wutilwin.LeftPressed() {
			dx--
		}
		if wutilwin.DownPressed() {
			dy++
		}
		if wutilwin.UpPressed() {
			dy--
		}
		if dx != 0 || dy != 0 {
			mag := math.Sqrt(float64(dx*dx + dy*dy))
			lock.Lock()
			targetX += float64(dx) / mag * 50
			targetY += float64(dy) / mag * 50
			wutilext.LogDetail(fmt.Sprintf("queued target now (%.1f, %.1f)", targetX, targetY), "nudge")
			lock.Unlock()
			time.Sleep(50 * time.Millisecond)
		}
		time.Sleep(10 * time.Millisecond)
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
