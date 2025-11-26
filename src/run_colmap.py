import os

scene_dir = "LightCity/F2_multi_circle"

os.system(f"rm {scene_dir}/database.db")

cmd = f"colmap feature_extractor \
   --database_path {scene_dir}/database.db \
    --ImageReader.camera_model PINHOLE \
    --ImageReader.single_camera 1 \
   --image_path {scene_dir}/images"
os.system(cmd)

cmd = f"colmap exhaustive_matcher \
   --database_path {scene_dir}/database.db"
os.system(cmd)

cmd = f"mkdir {scene_dir}/sparse"
os.system(cmd)

cmd = f"colmap mapper \
    --database_path {scene_dir}/database.db \
    --image_path {scene_dir}/images \
    --output_path {scene_dir}/sparse"
os.system(cmd)