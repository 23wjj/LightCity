# Given ground-truth camera poses，convert the data into colmap format
# reference https://colmap.github.io/faq.html#reconstruct-sparse-dense-model-from-known-camera-poses
import os
import re
import numpy as np
# import mathutils
from scipy.spatial.transform import Rotation as R
import json
import shutil

def choose_recon_data(sky_dst_dir, street_dst_dir, test_dst_dir, target_dir):
    
    info_sky_dir = sky_dst_dir.replace("render", "info")
    info_street_dir = street_dst_dir.replace("render", "info")
    info_test_dir = test_dst_dir.replace("render", "info")
    os.makedirs(target_dir, exist_ok=True)
    base_dir = os.path.dirname(target_dir)
    shutil.copy(os.path.join(info_sky_dir, "cam2hdr_info.json"), os.path.join(base_dir, "sky_cam2hdr_info.json"))
    shutil.copy(os.path.join(info_sky_dir, "camera_input.json"), os.path.join(base_dir, "sky_camera_input.json"))
    shutil.copy(os.path.join(info_street_dir, "cam2hdr_info.json"), os.path.join(base_dir, "street_cam2hdr_info.json"))
    shutil.copy(os.path.join(info_street_dir, "camera_input.json"), os.path.join(base_dir, "street_camera_input.json"))
    shutil.copy(os.path.join(info_test_dir, "cam2hdr_info.json"), os.path.join(base_dir, "test_cam2hdr_info.json"))
    shutil.copy(os.path.join(info_test_dir, "camera_input.json"), os.path.join(base_dir, "test_camera_input.json"))
    
    step = 1
    pattern = re.compile(r"^\d{5}\.png$")
    sky_image_files = sorted([f"{f}" for f in os.listdir(sky_dst_dir) if pattern.match(f)])
    sky_bias = len(sky_image_files)
    street_image_files = sorted([f"{int(f[:-4]) + sky_bias:05d}.png" for f in os.listdir(street_dst_dir) if pattern.match(f)])
    recon_images = sky_image_files + street_image_files
    
    if step > 1:
        recon_images = recon_images[::]
    
    train_bias = len(recon_images)
    test_image_files = sorted([f"{int(f[:-4]) + train_bias:05d}.png" for f in os.listdir(test_dst_dir) if pattern.match(f)])
    
    total_images = recon_images + test_image_files
    
    for img in total_images:
        if int(img[:-4]) < sky_bias:
            src_path = os.path.join(sky_dst_dir, img)
            target_path = os.path.join(target_dir, img)
        elif int(img[:-4]) < train_bias:
            # street
            true_img = f"{int(img[:-4]) - sky_bias:05d}.png"
            src_path = os.path.join(street_dst_dir, true_img)
            target_path = os.path.join(target_dir, img)
        else:
            # test
            true_img = f"{int(img[:-4]) - train_bias:05d}.png"
            src_path = os.path.join(test_dst_dir, true_img)
            target_path = os.path.join(target_dir, img)
            
        # else:
        #     raise ValueError
        
        shutil.copy(src_path, target_path)
        
    print(f"{len(total_images)} images copied in total.")
    return sky_bias, train_bias
        

def get_cameras_data():
    # we use the same camera intrinsic
    camera_id = 0
    model = "PINHOLE"
    width = 1024
    height = 768
    fx = 50 * width / 36
    fy = fx
    cx = 512
    cy = 384
    camera_data = (camera_id, model, width, height, fx, fy, cx, cy)
    
    return camera_data

def rotmat2qvec(R):
    Rxx, Ryx, Rzx, Rxy, Ryy, Rzy, Rxz, Ryz, Rzz = R.flat
    K = (
        np.array(
            [
                [Rxx - Ryy - Rzz, 0, 0, 0],
                [Ryx + Rxy, Ryy - Rxx - Rzz, 0, 0],
                [Rzx + Rxz, Rzy + Ryz, Rzz - Rxx - Ryy, 0],
                [Ryz - Rzy, Rzx - Rxz, Rxy - Ryx, Rxx + Ryy + Rzz],
            ]
        )
        / 3.0
    )
    eigvals, eigvecs = np.linalg.eigh(K)
    qvec = eigvecs[[3, 0, 1, 2], np.argmax(eigvals)]
    if qvec[0] < 0:
        qvec *= -1
    return qvec
def get_images_data(camera_pose_json, image2camera_json, image_files, label, bias):
    
    with open(camera_pose_json, "r", encoding="utf-8") as f:
        camera_data = json.load(f)
    with open(image2camera_json, "r", encoding="utf-8") as f:
        image2camera = json.load(f)

    camera_poses = {}
    for camera_pose_id in camera_data.keys():
        camera_pose = camera_data[camera_pose_id]
        c2w = np.array(camera_pose["transform_matrix"])       
        c2w[:3, 1:3] *= -1
        w2c = np.linalg.inv(c2w)
        R_colmap = w2c[:3, :3]
        t_colmap = w2c[:3, 3]        
        qvec = rotmat2qvec(R_colmap)
        
        camera_poses[camera_pose_id] = {"tvec": t_colmap, "qvec": qvec}
        
    images_data = []
    camera_id = 0
    # __import__('ipdb').set_trace()
    for image_id in image2camera.keys():
        camera_pose_id = image2camera[image_id]["camera"]
        image_name = image2camera[image_id]["name"]
        # if label == "sky":
        #     pass
        if label == "sky" and f"{image_name}.png" not in image_files:
            continue
        if label == "street" and f"{int(image_name) + bias:05d}.png" not in image_files:
            continue
        if label == "test" and f"{int(image_name) + bias:05d}.png" not in image_files:
            continue
        camera_pose = camera_poses[str(camera_pose_id)]
        tvec = camera_pose["tvec"]
        qvec = camera_pose["qvec"]
        # IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
        img_data = []
        # img_data.append(image_id)
        img_data.append(qvec)
        # img_data.append(qvec[0: 3])
        img_data.append(tvec)
        img_data.append(camera_id)
        if label == "sky":
            img_data.append(f"{image_name}.png")
        elif label == "street" or label == "test":
            img_data.append(f"{int(image_name) + bias:05d}.png")
        images_data.append(img_data)
    
    return images_data
        
    

if __name__ == "__main__":
    
    base_dir = "LightCity"
    scenes = ["F2_multi_circle"]
    
    for scene in scenes:
        sky_dst_dir = "LightCity/render_F2_sky_large_range"
        street_dst_dir = "LightCity/render_F2_street_large_range"
        test_dst_dir = "LightCity/render_F2_test_large_range"
        scene_path = os.path.join(base_dir, scene)
        target_dir = os.path.join(scene_path, "images")
        
        # sky images number sky+street
        # sky_bias, train_bias = choose_recon_data(sky_dst_dir, street_dst_dir, test_dst_dir,target_dir)
        sky_bias = 236
        os.system(f"rm -rf {scene_path}/database.db")
        os.system(f"rm -rf {scene_path}/sparse")
        manually_colmap_dir = os.path.join(scene_path, "manually_sparse")
        os.makedirs(manually_colmap_dir, exist_ok=True)
        sky_camera_pose_json = os.path.join(scene_path, "sky_camera_input.json")
        sky_image2camera_json = os.path.join(scene_path, "sky_cam2hdr_info.json")
        street_camera_pose_json = os.path.join(scene_path, "street_camera_input.json")
        street_image2camera_json = os.path.join(scene_path, "street_cam2hdr_info.json")
        test_camera_pose_json = os.path.join(scene_path, "test_camera_input.json")
        test_image2camera_json = os.path.join(scene_path, "test_cam2hdr_info.json")
        
        # 1. get camera intrinsics, write cameras.txt
        #   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
        # Model: PINHOLE
        cameras_path = os.path.join(manually_colmap_dir, "cameras.txt")
        camera_data = get_cameras_data()
        with open(cameras_path, "w", encoding="utf-8") as f:
            data_str = ' '.join(str(item) for item in camera_data)
            f.write(data_str)
        
        # 2. get camera pose, write images.txt
        #   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
        images_path = os.path.join(manually_colmap_dir, "images.txt")
        images_dir = os.path.join(scene_path, "images")
        image_files = sorted(os.listdir(images_dir))
        sky_images_data = get_images_data(camera_pose_json=sky_camera_pose_json, image2camera_json=sky_image2camera_json, image_files=image_files, label="sky", bias=sky_bias)
        street_images_data = get_images_data(camera_pose_json=street_camera_pose_json, image2camera_json=street_image2camera_json, image_files=image_files, label="street", bias=sky_bias)
        # test_images_data = get_images_data(camera_pose_json=test_camera_pose_json, image2camera_json=test_image2camera_json, image_files=image_files, label="test", bias=train_bias)
        
        images_data = sky_images_data + street_images_data # + test_images_data
        # __import__('ipdb').set_trace()
        # write images.txt
        with open(images_path, "w", encoding="utf-8") as f:
            for id, data in enumerate(images_data):
                # add image id
                data_flat = [str(id)] + [str(item) if not isinstance(item, np.ndarray) else ' '.join(map(str, item)) for item in data]
                f.write(' '.join(data_flat) + "\n")
                f.write("\n")
        
        # 3. create an empty points3D.txt
        point3d_path = os.path.join(manually_colmap_dir, "points3D.txt")
        with open(point3d_path, "w") as f:
            pass
        
        cmd = f"colmap feature_extractor \
            --database_path {scene_path}/database.db \
            --ImageReader.camera_model PINHOLE \
            --image_path {scene_path}/images"
        os.system(cmd)
        
    
        cmd = f"colmap exhaustive_matcher \
            --database_path {scene_path}/database.db"
        os.system(cmd)
        
        output_dir = os.path.join(scene_path, "sparse")
        os.makedirs(output_dir, exist_ok=True)
        cmd = f"colmap point_triangulator \
            --database_path {scene_path}/database.db \
            --image_path {scene_path}/images \
            --input_path {manually_colmap_dir} \
            --output_path {output_dir}"
        os.system(cmd)

        # write split file
        llffhold = 8
        total_images = sorted(os.listdir(target_dir))
        test_images = total_images[::llffhold]
        train_images = [image for image in total_images if image not in test_images]
        
        # __import__('ipdb').set_trace()
        # scene_name.tsv
        output_tsv = os.path.join(scene_path, f"{scene}.tsv")
        data = []
        for id, f in enumerate(total_images):
            log_data = {}
            log_data["filename"] = f
            log_data["id"] = id
            log_data["dataset"] = scene
            if f in train_images:
                log_data["split"] = "train"
            elif f in test_images:
                log_data["split"] = "test"
            else:
                raise ValueError("image not in train or test")
            data.append(log_data)
        
        with open(output_tsv, "w", newline="", encoding="utf-8") as file:
            filenames = ["filename", "id", "split", "dataset"]
            writer = csv.DictWriter(file, fieldnames=filenames, delimiter="\t")
            writer.writeheader()
            writer.writerows(data)
        
        # nerfw_split.csv
        output_csv = os.path.join(scene_path, f"nerfw_split.csv")
        with open(output_csv, "w", newline="", encoding="utf-8") as file:
            filenames = ["filename", "id", "split", "dataset"]
            writer = csv.DictWriter(file, fieldnames=filenames, delimiter="\t")
            writer.writeheader()
            writer.writerows(data)
            
        # test_list.txt train_list.txt
        with open(f'{scene_path}/train_list.txt', 'w') as file:
            for filename in train_images:
                file.write(filename + '\n')
        with open(f'{scene_path}/test_list.txt', 'w') as file:
            for filename in test_images:
                file.write(filename + '\n')
        
        # test.txt
        with open(f'{scene_path}/test.txt', 'w') as file:
            for filename in test_images:
                file.write(filename + '\n')