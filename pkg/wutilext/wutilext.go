package wutilext

import (
	"fmt"
	"os"
	"time"
)

type debugSettings struct {
	showMarks    bool
	showLogs     bool
	verboseMarks bool
	verboseLogs  bool
}

var modes = map[string]debugSettings{
	"off":    {},
	"lite":   {showMarks: true, showLogs: true},
	"normal": {showMarks: true, showLogs: true},
	"speed":  {showMarks: true, verboseMarks: true},
	"hard":   {showMarks: true, showLogs: true, verboseMarks: true, verboseLogs: true},
}

var mode = os.Getenv("WUTIL_DEBUG_MODE")
var start = time.Now()
var last = start

func RealCWD() string {
	if cwd := os.Getenv("WUTIL_REAL_CWD"); cwd != "" {
		return cwd
	}
	cwd, _ := os.Getwd()
	return cwd
}

func Root() string {
	if root := os.Getenv("WUTIL_ROOT"); root != "" {
		return root
	}
	cwd, _ := os.Getwd()
	return cwd
}

func Mark(label string, source string) {
	mark(label, true, source)
}

func MarkDetail(label string, source string) {
	mark(label, false, source)
}

func Log(message string, source string) {
	log(message, true, source)
}

func LogDetail(message string, source string) {
	log(message, false, source)
}

func mark(label string, important bool, source string) {
	now := time.Now()
	total := now.Sub(start).Seconds()
	since := now.Sub(last).Seconds()
	last = now
	settings := modes[currentMode()]
	if settings.showMarks && (important || settings.verboseMarks) {
		fmt.Printf("[debug:%s] [mark:%s] [%s] %s | total %.3fs | +%.3fs\n", currentMode(), level(important), source, label, total, since)
	}
}

func log(message string, important bool, source string) {
	settings := modes[currentMode()]
	if settings.showLogs && (important || settings.verboseLogs) {
		fmt.Printf("[debug:%s] [log:%s] [%s] +%.3fs %s\n", currentMode(), level(important), source, time.Since(start).Seconds(), message)
	}
}

func currentMode() string {
	if _, ok := modes[mode]; ok {
		return mode
	}
	return "off"
}

func level(important bool) string {
	if important {
		return "main"
	}
	return "detail"
}
