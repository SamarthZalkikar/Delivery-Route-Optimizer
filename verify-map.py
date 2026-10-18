"""verify-map.py -- offline STEP-1/2 evidence for the real-map upgrade.

No browser is available in this environment (headless Firefox fails with
GFX1- RenderCompositorSWGL and produces no screenshot), so this script
verifies every deterministic fact a browser probe would have collected,
by fetching the LIVE server's HTML/CSS/JS and asserting each checklist
item. Items it cannot check headlessly are printed as MANUAL at the end.
"""
