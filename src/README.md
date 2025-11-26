## Installation
* blender 3.6
* SceneCity 1.9.3 add-on
* EasyHDRI-1.1.1 add-on

## Rendering
This only provides an example script for self rendering after building your own city assets.
```bash
./blender -b lightcity.blend -P render.py -- -sb 120 -se 201 -s 512 -rx 1024 -ry 768 -cp 16
```

## Camera Pose Conversion
```convert.py``` provides an example code for converting cameras from blender format into colmap format.