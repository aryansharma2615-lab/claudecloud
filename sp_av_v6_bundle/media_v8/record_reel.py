import os, glob
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True,
                        record_video_dir="/tmp/claude-0/vid", record_video_size={"width": 780, "height": 1688})
    pg = ctx.new_page()
    pg.goto("file://" + os.path.abspath("servo_mount_v8.html")); pg.wait_for_timeout(3000)
    js = pg.evaluate
    js("() => __avV8.setPhase('load')"); pg.wait_for_timeout(1800)
    js("() => __avV8.view({yaw: -0.5})"); pg.wait_for_timeout(600)
    js("() => __avV8.setPhase('fit')"); pg.wait_for_timeout(3500)
    js("() => __avV8.setPhase('secure')"); pg.wait_for_timeout(9000)
    js("() => __avV8.setPhase('test')"); pg.wait_for_timeout(1800)
    for kg in (0.3, 0.45, 0.6, 1.0, 1.6, 2.2):
        js(f"() => __avV8.setLoad({kg}, 35)"); pg.wait_for_timeout(700)
    js("() => document.getElementById('v8Sweep').click()"); pg.wait_for_timeout(5500)
    js("() => { __avV8.setWire(true); __avV8.section({axis: 0, at: 2.0}); }"); pg.wait_for_timeout(2500)
    ctx.close(); b.close()
print(glob.glob("/tmp/claude-0/vid/*.webm"))
