import os
import numpy as np
import cv2
import glob
import json

os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

if __name__ == '__main__':
    
    dst_dir = "render_new"
    target_dir = "invalid_renders"
    os.makedirs(target_dir, exist_ok=True)
    threshold = 3
    del_log_file = f"{dst_dir}/00000_deleted_files.json"
    move_log_file = f"{dst_dir}/00000_move_files.json"
    # For single render, we have information including:
    # name.png, name_Albedo*.png, name_Depth*.exr, name_Environment*.png, 
    # name_Image*.png, name_Normal*.png, name_Objects*.exr, name_Shading*.png
    pattern = os.path.join(dst_dir, "*_Obejcts*.exr")
    exr_files = sorted(glob.glob(pattern))
    
    # print(exr_files)
    deleted_cnt = 0
    deleted_data = []
    move_cnt = 0
    move_data = []
    for file in exr_files:
        object_ids = cv2.imread(file, cv2.IMREAD_UNCHANGED)
        
        if object_ids is None:
            raise ValueError(f"Failed to load : {file}")
        
        object_id_map = object_ids[:, :, 0]
        unique_ids = np.unique(object_id_map)
        
        num_objects = len(unique_ids)
        
        image_id = os.path.basename(file).split("_Obejcts")[0]
        
        if num_objects == 1 and object_id_map[0][0] == 0:
            # if object_id_map[0] == 0:
            os.system(f"rm {dst_dir}/{image_id}.png")
            os.system(f"rm {dst_dir}/{image_id}_*")
            print(f"Deleted all contents of {image_id}.png")
            print(f"Objects num is {num_objects}")

            log_data = {"image_id": image_id}
            deleted_data.append(log_data)
            deleted_cnt = deleted_cnt + 1
            continue
                
        if num_objects <= threshold:
            # __import__('ipdb').set_trace()
            os.system(f"mv {dst_dir}/{image_id}.png {target_dir}/")
            os.system(f"mv {dst_dir}/{image_id}_* {target_dir}")
            print(f"Move all contents of {image_id}.png")
            print(f"Objects num is {num_objects}")

            log_data = {"image_id": image_id}
            move_data.append(log_data)
            move_cnt = move_cnt + 1
            
            # break
    
    deleted_data.append({"total deleted num": deleted_cnt})
    with open(del_log_file, "w") as f:
        json.dump(deleted_data, f, indent=4)
            # break
            
    move_data.append({"total move num": move_cnt})
    with open(move_log_file, "w") as f:
        json.dump(move_data, f, indent=4)