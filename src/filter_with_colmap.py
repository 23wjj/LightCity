import sqlite3
import os
import json

import os

images_txt_path = "LightCity/F2_multi_circle/sparse/txt/images.txt" # colmap registration results
image_folder = "LightCity/F2_multi_circle/images"  # folder of original rendered images

registered_images = set()
with open(images_txt_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in lines:
    if line.strip() and not line.startswith("#"): 
        parts = line.split()
        if len(parts) > 1:
            registered_images.add(parts[-1]) 


all_images = {img for img in os.listdir(image_folder) if img.lower().endswith(('.jpg', '.png', '.jpeg'))}
registered_images = {img for img in registered_images if img.lower().endswith(('.jpg', '.png', '.jpeg'))}

unregistered_images = all_images - registered_images

# 打印结果
print(f"Total images: {len(all_images)}")
print(f"Registered number: {len(registered_images)}")
print(f"Fail to register: {len(unregistered_images)}")
print("List of images failed to register:", unregistered_images)

# print("Unregistered images list:", unregistered_images)
output_file = os.path.join(os.path.dirname(image_folder), "unregistered_images.json")
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(list(unregistered_images), f, indent=4, ensure_ascii=False)

dst_path = image_folder.replace("colmap", "filtered")
images = os.listdir(dst_path)
for img in images:
    if img in unregistered_images:
        os.system(f"rm -rf {dst_path}/{img}")
        print(f"Delete {dst_path}/{img}")