-- 切换 iPhone Mirroring 设备
-- 用法: osascript switch_to_iphone_mirroring.applescript "iPhone 287"
--   或: osascript switch_to_iphone_mirroring.applescript "iPhone 288"

on run argv
	if (count of argv) = 0 then
		display dialog "请选择要镜像的 iPhone：" buttons {"iPhone 287", "iPhone 288"} default button 1
		set targetDevice to button returned of result
	else
		set targetDevice to item 1 of argv
	end if

	-- 打开系统设置 > 桌面与程序坞，读取当前设备
	do shell script "open 'x-apple.systempreferences:com.apple.Desktop-Settings'"
	delay 1.5

	set needSwitch to false
	tell application "System Events"
		tell process "System Settings"
			tell window 1
				set ec to entire contents
				repeat with elem in ec
					try
						if class of elem is pop up button and name of elem is "iPhone" then
							set currentValue to value of elem
							if currentValue is targetDevice then
								-- 已经是目标设备，无需切换
								log "Already connected to " & targetDevice
							else
								-- 切换设备
								click elem
								delay 0.5
								click menu item targetDevice of menu 1 of elem
								delay 1
								set needSwitch to true
								log "Switched to " & targetDevice
							end if
							exit repeat
						end if
					end try
				end repeat
			end tell
		end tell
	end tell

	-- 关闭系统设置
	tell application "System Settings" to quit

	if needSwitch then
		-- 切换后等待并启动 iPhone Mirroring
		delay 3
		tell application "iPhone Mirroring" to activate
	end if
end run