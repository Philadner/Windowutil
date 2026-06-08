package wutilwin

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"

	"windowutil/pkg/wutilext"
)

type Window struct {
	Handle uintptr
	title  string
}

type Bounds struct {
	Left   int
	Top    int
	Width  int
	Height int
}

type rect struct {
	Left   int32
	Top    int32
	Right  int32
	Bottom int32
}

const (
	smCXScreen = 0
	smCYScreen = 1

	vkEscape = 0x1B
	vkLeft   = 0x25
	vkUp     = 0x26
	vkRight  = 0x27
	vkDown   = 0x28

	processQueryLimitedInformation = 0x1000
)

var (
	user32                = syscall.NewLazyDLL("user32.dll")
	procEnumWindows       = user32.NewProc("EnumWindows")
	procIsWindowVisible   = user32.NewProc("IsWindowVisible")
	procGetWindowTextW    = user32.NewProc("GetWindowTextW")
	procGetWindowTextLenW = user32.NewProc("GetWindowTextLengthW")
	procGetWindowRect     = user32.NewProc("GetWindowRect")
	procMoveWindow        = user32.NewProc("MoveWindow")
	procGetSystemMetrics  = user32.NewProc("GetSystemMetrics")
	procGetAsyncKeyState  = user32.NewProc("GetAsyncKeyState")
	procSetProcessDPI     = user32.NewProc("SetProcessDPIAware")
	procGetWindowPID      = user32.NewProc("GetWindowThreadProcessId")

	kernel32                  = syscall.NewLazyDLL("kernel32.dll")
	procOpenProcess           = kernel32.NewProc("OpenProcess")
	procCloseHandle           = kernel32.NewProc("CloseHandle")
	procQueryFullProcessImage = kernel32.NewProc("QueryFullProcessImageNameW")
)

func init() {
	_, _, _ = procSetProcessDPI.Call()
}

func All() ([]Window, error) {
	windows := []Window{}
	callback := syscall.NewCallback(func(hwnd uintptr, lparam uintptr) uintptr {
		if !isVisible(hwnd) {
			return 1
		}
		title := titleOf(hwnd)
		if strings.TrimSpace(title) == "" {
			return 1
		}
		windows = append(windows, Window{Handle: hwnd, title: title})
		return 1
	})
	ret, _, err := procEnumWindows.Call(callback, 0)
	if ret == 0 {
		return nil, err
	}
	return windows, nil
}

func FindByTitle(fragment string) ([]Window, error) {
	all, err := All()
	if err != nil {
		return nil, err
	}
	term := strings.ToLower(fragment)
	matches := []Window{}
	for _, win := range all {
		if strings.Contains(strings.ToLower(win.Title()), term) {
			matches = append(matches, win)
		}
	}
	return matches, nil
}

func LoadSelected() (*Window, error) {
	data, err := os.ReadFile(statePath())
	if err != nil {
		return nil, nil
	}
	var state struct {
		Title string `json:"title"`
	}
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, err
	}
	matches, err := FindByTitle(state.Title)
	if err != nil || len(matches) == 0 {
		return nil, err
	}
	return &matches[0], nil
}

func SaveSelected(win Window) error {
	data, err := json.Marshal(map[string]string{"title": win.Title()})
	if err != nil {
		return err
	}
	return os.WriteFile(statePath(), data, 0644)
}

func ScreenSize() (int, int) {
	width, _, _ := procGetSystemMetrics.Call(uintptr(smCXScreen))
	height, _, _ := procGetSystemMetrics.Call(uintptr(smCYScreen))
	return int(width), int(height)
}

func EscapePressed() bool {
	return keyPressed(vkEscape)
}

func LeftPressed() bool {
	return keyPressed(vkLeft)
}

func RightPressed() bool {
	return keyPressed(vkRight)
}

func UpPressed() bool {
	return keyPressed(vkUp)
}

func DownPressed() bool {
	return keyPressed(vkDown)
}

func (win Window) Title() string {
	if win.title != "" {
		return win.title
	}
	return titleOf(win.Handle)
}

func (win Window) ProcessID() uint32 {
	var pid uint32
	procGetWindowPID.Call(win.Handle, uintptr(unsafe.Pointer(&pid)))
	return pid
}

func (win Window) ExePath() string {
	pid := win.ProcessID()
	if pid == 0 {
		return ""
	}
	handle, _, _ := procOpenProcess.Call(processQueryLimitedInformation, 0, uintptr(pid))
	if handle == 0 {
		return ""
	}
	defer procCloseHandle.Call(handle)

	buffer := make([]uint16, syscall.MAX_PATH*4)
	size := uint32(len(buffer))
	ret, _, _ := procQueryFullProcessImage.Call(
		handle,
		0,
		uintptr(unsafe.Pointer(&buffer[0])),
		uintptr(unsafe.Pointer(&size)),
	)
	if ret == 0 {
		return ""
	}
	return syscall.UTF16ToString(buffer[:size])
}

func (win Window) ExeName() string {
	exePath := win.ExePath()
	if exePath == "" {
		return ""
	}
	return filepath.Base(exePath)
}

func (win Window) Bounds() (Bounds, error) {
	var r rect
	ret, _, err := procGetWindowRect.Call(win.Handle, uintptr(unsafe.Pointer(&r)))
	if ret == 0 {
		return Bounds{}, err
	}
	return Bounds{
		Left:   int(r.Left),
		Top:    int(r.Top),
		Width:  int(r.Right - r.Left),
		Height: int(r.Bottom - r.Top),
	}, nil
}

func (win Window) MoveTo(left int, top int) error {
	bounds, err := win.Bounds()
	if err != nil {
		return err
	}
	return win.MoveResize(left, top, bounds.Width, bounds.Height)
}

func (win Window) ResizeTo(width int, height int) error {
	bounds, err := win.Bounds()
	if err != nil {
		return err
	}
	return win.MoveResize(bounds.Left, bounds.Top, width, height)
}

func (win Window) MoveResize(left int, top int, width int, height int) error {
	ret, _, err := procMoveWindow.Call(
		win.Handle,
		uintptr(left),
		uintptr(top),
		uintptr(width),
		uintptr(height),
		1,
	)
	if ret == 0 {
		return err
	}
	return nil
}

func RequireSelected(source string) (*Window, error) {
	win, err := LoadSelected()
	if err != nil {
		return nil, err
	}
	if win == nil {
		wutilext.Log("no saved window state file found", source)
		return nil, fmt.Errorf("No window selected. Use 'sel <name>' first.")
	}
	return win, nil
}

func isVisible(hwnd uintptr) bool {
	ret, _, _ := procIsWindowVisible.Call(hwnd)
	return ret != 0
}

func titleOf(hwnd uintptr) string {
	length, _, _ := procGetWindowTextLenW.Call(hwnd)
	if length == 0 {
		return ""
	}
	buffer := make([]uint16, length+1)
	procGetWindowTextW.Call(hwnd, uintptr(unsafe.Pointer(&buffer[0])), uintptr(len(buffer)))
	return syscall.UTF16ToString(buffer)
}

func keyPressed(vk int) bool {
	state, _, _ := procGetAsyncKeyState.Call(uintptr(vk))
	return state&0x8000 != 0
}

func statePath() string {
	return filepath.Join(wutilext.Root(), ".windowutil_state.json")
}
