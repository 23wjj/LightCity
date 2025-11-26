import bpy
import math
import os 
import random
import numpy as np
import math
import mathutils
import json
import argparse
import sys

sb = 0
se = -1
cp = 8  
rx = 1024
ry = 768
s = 512

class ArgumentParserForBlender(argparse.ArgumentParser):
    def _get_argv_after_doubledash(self):
        try:
            idx = sys.argv.index('--')
            argv = sys.argv[idx+1:]
        except ValueError as e:
            argv = []
        return argv
    def parse_args(self):
        return super().parse_args(args=self._get_argv_after_doubledash())
parser = ArgumentParserForBlender()
parser.add_argument("-sb", "--streetb", dest="sb", type=int, default=0, required=True)
parser.add_argument("-se", "--streete", dest="se", type=int, default=-1, required=True)
parser.add_argument("-cp", "--campos", dest="cp", type=int, default=16)
parser.add_argument("-rx", "--resx", dest="rx", type=int, default=1024)
parser.add_argument("-ry", "--resy", dest="ry", type=int, default=768)
parser.add_argument("-s", "--sample", dest="s", type=int, default=512)
args = parser.parse_args()

se = args.se
sb = args.sb
cp = args.cp
rx = args.rx
ry = args.ry
s = args.s
print(f"se:{se}, sb:{sb}, cp:{cp}, rx:{rx}, ry:{ry}, s:{s}")
# get scene information
CAM_POSE = cp
bpy.data.scenes["Scene"].render.image_settings.file_format = 'PNG'

range_z = [[0.5, 1.5], [2.5, 4.0]]
range_z_euler = [0.0, 360.0]
scale_y_euler = 10.0
range_x_euler = [[50, 100], [30, 90]]

cameras_centers = []
cameras_poses = []

RENDER_PATH = 'render_new'
INFO_PATH = 'info_new'
hdri_dir = "SKY_HDRI/"

object_info = "object_info.json"
hdri_info = "hdri_info.json"
camera_info = "camera_info.json"
cam2hdr_info = "cam2hdr_info.json"
caminput_info = "camera_input.json"

semantic_dict = {"FL13_2": "plant", 
                 "flower pot": "plant",
                 "SC plant": "plant",
                 "SC road": "road", 
                 "pole": "light pole",
                 "SC street light": "light pole",
                 "collier": "light pole",
                 "post clamp": "light pole",
                 "Fire hydrant": "fire hydrant",
                 "SC building": "building",
                 "street name": "street name",
                 "pedestrian light": "pedestrian light",
                 "traffic light": "traffic light",
                 "building": "building",
                 "European": "tree",
                 "jardiniere": "tree base",
                 "water tower": "water tower",
                 "bus stop": "bus stop",
                 "bin": "bin",
                 "vent": "vent",
                 "air duct": "air duct",
                 "billboard": "billboard",
                 "advert": "advert",
                 "mailbox": "mailbox",
                 }

def r2a(r):
    return r/math.pi*18.0
    
def a2r(a):
    return a/180.0*math.pi

def save_json(directory, filename, data, indent=4):
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w') as file:
        json.dump(data, file, indent=indent)
            
def set_objects_num():
    objects = bpy.data.objects
    index = 1
    object_dict = {}
    for i in range(len(objects)):
        if objects[i].type == "CAMERA":
            continue
        elif objects[i].type == "EMPTY":
            objects[i].pass_index = 0
            continue
        objects[i].pass_index = index
        object_dict[objects[i].name] = index
        index += 1
    # write to txt
    save_json(INFO_PATH, object_info, object_dict)

def set_hdri_list(all_hdri):
    # write to txt
    hdri_dict = dict(zip(list(range(len(all_hdri))), all_hdri))
    save_json(INFO_PATH, hdri_info, hdri_dict)
    return hdri_dict

def listify_matrix(matrix):
    matrix_list = []
    for row in matrix:
        matrix_list.append(list(row))
    return matrix_list

def listify_vector(vector):
    vector_list = [] 
    for i in range(len(vector)):
        vector_list.append(vector[i])
    return vector_list

def get_camera_params(camera):
    camera_angle_x = camera.data.angle_x
    camera_angle_y = camera.data.angle_y

    # camera properties
    f_in_mm = camera.data.lens # focal length in mm
    scale = 1.0
    width_res_in_px = bpy.context.scene.render.resolution_x  * scale # width
    height_res_in_px = bpy.context.scene.render.resolution_y * scale # height
    optical_center_x = width_res_in_px / 2
    optical_center_y = height_res_in_px / 2

    # pixel aspect ratios
    size_x = width_res_in_px
    size_y = height_res_in_px
    pixel_aspect_ratio = 1.0

    # sensor fit and sensor size (and camera angle swap in specific cases)
    
    sensor_size_in_mm = camera.data.sensor_width
    sensor_fit = 'HORIZONTAL'

    # focal length for horizontal sensor fit
    if sensor_fit == 'HORIZONTAL':
        sensor_size_in_mm = camera.data.sensor_width
        s_u = f_in_mm / sensor_size_in_mm * width_res_in_px
        s_v = f_in_mm / sensor_size_in_mm * width_res_in_px * pixel_aspect_ratio
    
    u_0 = width_res_in_px * scale / 2
    v_0 = height_res_in_px * scale / 2
    skew = 0 # only use rectangular pixels

#    K = Matrix(
#        ((s_u, skew,    u_0),
#        (    0  , s_v, v_0),
#        (    0  , 0,        1 )))
    return s_u, s_v, u_0, v_0
   
def record_cameras(streets=None):
    camera_dict = {}
    all_cameras = list(filter(lambda o: o.type == 'CAMERA', bpy.data.objects))
    if streets is not None:
    	pass
    else:
        streets = [0 for i in range(len(all_cameras))]
    assert len(streets) == len(all_cameras)
    
    for idx, camera in enumerate(all_cameras):
        s_u, s_v, u_0, v_0 = get_camera_params(camera)
        camera_dict[idx] = {}
        camera_dict[idx]["street"] = streets[idx]
        camera_dict[idx]["name"] = camera.name
        camera_dict[idx]["location"] = listify_vector(camera.location)
        camera_dict[idx]["rotation_euler"] = listify_vector(camera.rotation_euler)
        # camera_dict[idx]["transform_matrix"] = listify_matrix(camera.matrix_world)
        camera_dict[idx]["su"] = s_u
        camera_dict[idx]["sv"] = s_v
        camera_dict[idx]["u0"] = u_0
        camera_dict[idx]["v0"] = v_0
        
    # write to txt
    save_json(INFO_PATH, camera_info, camera_dict)
    return
        
# camera trajectory generating

def get_all_street():
    all_street_name = []
    street_name = "Example grid city - SC road 1x1" # size 10x10
    objects = bpy.data.objects
    for i in range(len(objects)):
        if objects[i].type != "EMPTY":
            continue
        name = objects[i].name
        if street_name not in name:
            continue
        all_street_name.append(name)
    return all_street_name

def generate_cameras(cameras_centers, cameras_poses, pose_num=CAM_POSE, sb=0, se=-1):
    all_streets = get_all_street()
    objects = bpy.data.objects
    streets = []
    if se==-1:
    	streets_idx  = list(range(sb, len(all_streets)))
    else:
        streets_idx  = list(range(sb, se))
    print(len(all_streets), sb, se, streets_idx)
    for idx in streets_idx:
        street = all_streets[idx]
        loc = objects[street].location
        for j in range(pose_num):
            x = random.randint(0, 10)
            y = random.randint(0, 10)
            choose_z = random.randint(0,1)
            z = random.uniform(range_z[choose_z][0], range_z[choose_z][1])
            camera_center = [loc[0]*0.1+(x-5)*0.1, loc[1]*0.1+(y-5)*0.1, z]
            cameras_centers += [camera_center]

            euler_z = random.uniform(range_z_euler[0], range_z_euler[1])
            euler_y = 0.0 # np.random.randn()*scale_y_euler
            euler_x = random.uniform(range_x_euler[choose_z][0], range_x_euler[choose_z][1])
            cameras_poses += [[a2r(euler_x), a2r(euler_y), a2r(euler_z)]]
            streets.append(street)
    return streets, cameras_centers, cameras_poses

def add_cameras(cameras_centers, cameras_poses, index_range):
    cam_objs = []
    for i in index_range:
        cam = bpy.data.cameras.new("Camera")
        cam_obj = bpy.data.objects.new(cam.name, cam)
        bpy.context.collection.objects.link(cam_obj)
        cam_obj.location[0] = cameras_centers[i][0]
        cam_obj.location[1] = cameras_centers[i][1]
        cam_obj.location[2] = cameras_centers[i][2]
        cam_obj.rotation_euler[0] = cameras_poses[i][0]
        cam_obj.rotation_euler[1] = cameras_poses[i][1]
        cam_obj.rotation_euler[2] = cameras_poses[i][2]
        cam_objs.append(cam_obj)
    return

def setup_rendering(engine, samples, device, res_x, res_y, file_format='PNG'):
    # renderer setting
    bpy.context.scene.render.image_settings.color_mode = 'RGBA'
    bpy.context.scene.render.image_settings.color_depth = '8'
    bpy.context.scene.render.image_settings.file_format = file_format
    bpy.context.scene.render.engine = engine
    bpy.context.scene.cycles.samples = samples
    bpy.context.scene.cycles.device = device
    bpy.context.scene.render.resolution_x = res_x
    bpy.context.scene.render.resolution_y = res_y
    bpy.context.scene.render.resolution_percentage = 100
    bpy.context.scene.render.film_transparent = False

def create_depth_nodes(base_path, nodes, links, render_layers, file_format='OPEN_EXR'):
    # Create depth output nodes
    depth_file_output = nodes.new(type="CompositorNodeOutputFile")
    depth_file_output.label = 'Depth Output'
    depth_file_output.base_path = base_path
    depth_file_output.file_slots[0].use_node_format = True
    depth_file_output.format.file_format = file_format
    depth_file_output.format.color_depth = '16'
    assert file_format == "OPEN_EXR"
    if file_format == 'OPEN_EXR':
        links.new(render_layers.outputs["Depth"], depth_file_output.inputs[0])
    else:
        depth_file_output.format.color_mode = "BW"
        map = nodes.new(type="CompositorNodeMapValue")
        map.offset = [-0.7]
        map.size = [0.5]
        map.use_min = True
        map.min = [0]

        links.new(render_layers.outputs['Depth'], map.inputs[0])
        links.new(map.outputs[0], depth_file_output.inputs[0])
    return {'Depth': depth_file_output}

def create_normal_nodes(base_path, nodes, links, render_layers, file_format='PNG'):
    
    scale_node = nodes.new(type="CompositorNodeMixRGB")
    scale_node.blend_type = 'MULTIPLY'
    # scale_node.use_alpha = True
    scale_node.inputs[2].default_value = (0.5, 0.5, 0.5, 1)
    links.new(render_layers.outputs['Normal'], scale_node.inputs[1])

    bias_node = nodes.new(type="CompositorNodeMixRGB")
    bias_node.blend_type = 'ADD'
    # bias_node.use_alpha = True
    bias_node.inputs[2].default_value = (0.5, 0.5, 0.5, 0)
    links.new(scale_node.outputs[0], bias_node.inputs[1])

    normal_file_output = nodes.new(type="CompositorNodeOutputFile")
    normal_file_output.label = 'Normal Output'
    normal_file_output.base_path = base_path
    normal_file_output.file_slots[0].use_node_format = True
    normal_file_output.format.file_format = file_format
    links.new(bias_node.outputs[0], normal_file_output.inputs[0])
    return {"Normal": normal_file_output}

map_dict = {'Albedo': 'DiffCol',
            'Direct': 'DiffDir',
            'Indirect': 'DiffInd',
            'Environment': 'Env',
            'Image': 'Image',
            }
            
def create_alpha_nodes(base_path, nodes, links, render_layers, name='Albedo', file_format='PNG'):
    alpha_nodes = nodes.new(type="CompositorNodeSetAlpha")
    links.new(render_layers.outputs[map_dict[name]], alpha_nodes.inputs['Image'])
    links.new(render_layers.outputs['Alpha'], alpha_nodes.inputs['Alpha'])

    alpha_file_output = nodes.new(type="CompositorNodeOutputFile")
    alpha_file_output.label = f'{name} Output'
    alpha_file_output.base_path = base_path
    alpha_file_output.file_slots[0].use_node_format = True
    alpha_file_output.format.file_format = file_format
    alpha_file_output.format.color_mode = 'RGBA'
    alpha_file_output.format.color_depth = '8'
    links.new(alpha_nodes.outputs['Image'], alpha_file_output.inputs[0])
    return {name: alpha_file_output}

def create_shading_nodes(base_path, nodes, links, render_layers, only_shading=False, file_format='PNG'):    
    if only_shading:
        alpha_shading = nodes.new(type="CompositorNodeSetAlpha")
        links.new(render_layers.outputs['Alpha'], alpha_shading.inputs['Alpha'])
        shading_node = nodes.new('CompositorNodeMath')
        shading_node.operation = 'ADD'
        links.new(render_layers.outputs['DiffDir'], shading_node.inputs[0])
        links.new(render_layers.outputs['DiffInd'], shading_node.inputs[1])
        shading_file_output = nodes.new(type="CompositorNodeOutputFile")
        shading_file_output.label = 'shading Output'
        shading_file_output.base_path = base_path
        shading_file_output.file_slots[0].use_node_format = True
        shading_file_output.format.file_format = file_format
        shading_file_output.format.color_mode = 'RGBA'
        shading_file_output.format.color_depth = '8'
        links.new(shading_node.outputs[0], alpha_shading.inputs['Image'])
        links.new(alpha_shading.outputs['Image'], shading_file_output.inputs[0])
        return {'Shading': shading_file_output}
    else:
        # output direct and indirect shading respectively
        direct_output = create_alpha_nodes(nodes, links, render_layers, name='Direct', file_format=file_format)
        indirect_output = create_alpha_nodes(nodes, links, render_layers, name='Indirect', file_format=file_format)
        direct_output.update(indirect_output)
        return direct_output
        
def create_object_nodes(base_path, nodes, links, render_layers, file_format='OPEN_EXR'):
    id_file_output = nodes.new(type="CompositorNodeOutputFile")
    id_file_output.label = 'ID Output'
    id_file_output.base_path = base_path
    id_file_output.file_slots[0].use_node_format = True
    id_file_output.format.file_format = file_format
    id_file_output.format.color_depth = '16'
    
    assert file_format == "OPEN_EXR"
    if file_format == "OPEN_EXR":
        links.new(render_layers.outputs["IndexOB"], id_file_output.inputs[0])
    else:
        id_file_output.format.color_mode = 'BW'
        divide_node = nodes.new(type="CompositorNodeMath")
        divide_node.operation = "DIVIDE"
        divide_node.use_clamp = False
        divide_node.inputs[1].default_value = 2**int(8)
        links.new(render_layers.outputs['IndexOB'], divide_node.inputs[0])
        links.new(divide_node.outputs[0], id_file_output.inputs[0])
    return {'Obejcts': id_file_output}
    
def setup_multichannel(path, use_diffuse=True, use_shading=True, only_shading=False, use_environment=True, use_object=True, use_depth=False, use_normal=False):
    # enable nodes editting
    bpy.context.scene.use_nodes = True
    # diffuse
    bpy.context.scene.view_layers['ViewLayer'].use_pass_diffuse_color = use_diffuse
    # direct shading
    bpy.context.scene.view_layers['ViewLayer'].use_pass_diffuse_direct = use_shading
    # indirect shading
    bpy.context.scene.view_layers['ViewLayer'].use_pass_diffuse_indirect = use_shading
    # background
    bpy.context.scene.view_layers['ViewLayer'].use_pass_environment = use_environment
    # objects
    bpy.context.scene.view_layers["ViewLayer"].use_pass_object_index = use_object
    # normal
    bpy.context.scene.view_layers["ViewLayer"].use_pass_normal = use_normal
    # Depth
    bpy.context.scene.view_layers["ViewLayer"].use_pass_z = use_depth

    nodes = bpy.context.scene.node_tree.nodes
    links = bpy.context.scene.node_tree.links
    # Clear default nodes
    for n in nodes:
        nodes.remove(n)
    
    output_nodes = {}
    
    # Create input render layer node
    render_layers = nodes.new('CompositorNodeRLayers')
    
    # depth nodes
    if use_depth:
        depth_node = create_depth_nodes(path, nodes, links, render_layers)
        output_nodes.update(depth_node)
        
    # normal nodes
    if use_normal:
        normal_node = create_normal_nodes(path, nodes, links, render_layers)
        output_nodes.update(normal_node)
    
    # diffuse nodes
    if use_diffuse:
        diffuse_node = create_alpha_nodes(path, nodes, links, render_layers, name="Albedo")
        output_nodes.update(diffuse_node)
    
    # shading nodes
    if use_shading:
        shading_node = create_shading_nodes(path, nodes, links, render_layers, only_shading)
        output_nodes.update(shading_node)
        
    # object nodes
    if use_object:
        object_node = create_object_nodes(path, nodes, links, render_layers)
        output_nodes.update(object_node)
        
    # environment nodes
    if use_environment:
        environment_node = create_alpha_nodes(path, nodes, links, render_layers, name='Environment')
        output_nodes.update(environment_node)
    
    render_node = create_alpha_nodes(path, nodes, links, render_layers, name="Image")
    output_nodes.update(render_node)
    
    return output_nodes
    

def setup_sky_hdri(hdri_dir):
    worlds = bpy.data.worlds
    if worlds[0].name == 'EasyHDR':
        pass
    else:
        bpy.ops.EasyHDR.create_world()
    assert bpy.data.worlds[0].name == "EasyHDR"
    
    bpy.context.scene.previews_dir = hdri_dir

def set_output_path(path, output_nodes):
    for key in output_nodes:
        output_nodes[key].file_slots[0].path = path + f"_{key}"
        
    return

def load_cameras(file):
    with open(file) as f:
        d = json.load(f)
    return d
def get_valid_hdri(thres=150.0):
    valid_hdrs = []
    # with open("SKY_HDRI/0000_intensity.json") as f:
    #     check_dict = json.load(f)
    black_list = ['HDRI-13', 'HDRI-17', 'HDRI-2', 'HDRI-24','HDRI-4','HDRI-8','HDRI-9',]
    for i in range(len(all_hdrs)):
        name = all_hdrs[i][:-4]
        print(name)
        if name[:-4] in black_list:
            continue
        # if "Dusk" in name:
        #     continue
        # if "Evening" in name:
        #     continue
        if "Night" in name:
            continue
        # read json 
        # intensity = check_dict[name]
        # if intensity > thres:
        valid_hdrs.append(i)
    return valid_hdrs

# def get_large_hdri():
#     valid_hdrs = []
#     for i in range(len(all_hdrs)):
#         name = all_hdrs[i]
#         if "xxxx" in name:
#             pass
#         # read json 
#         intensity = check_dict[name]
#         if intensity > thres:
#             valid_hdrs.append(i)
#     return valid_hdrs

def record_hdri_camera(camera_num, hdri_num, all_cameras, select_hdri=2, select_rot=4):
    cam2hdr_dict = {}
    total_num = 0 
    # valid_list = get_valid_hdri()
    # small range
    # valid_list = [86, 91, 92, 93, 94, 133, 134, 136, 137, 139, 73, 75, 76, 
    #             77, 80, 82, 83, 161, 162, 163, 164, 165, 166, 167, 168, 
    #             169, 171, 172, 173, 174, 179, 180, 181, 182, 199]
    for i in range(camera_num):
        # choose_hdri = random.sample(valid_list, select_hdri)
        choose_hdri = random.sample(list(range(0, len(all_hdrs))), select_hdri)
        # choose_hdri = [73]
        euler = all_cameras[i].rotation_euler[2]
        x = random.randint(0,3)
        sky = 1.0
        if x == 1:
            sky = 2.0
        elif x>1:
            sky = 3.0
        # select_rot = 1
        for hdri in choose_hdri:
            for j in range(select_rot):
                # rot = random.uniform(0.0, 360.0)
                # rot = 0.0
                # rot = [0, 90, 180]
                rot = random.uniform(0.0, 90.0)*j + r2a(euler)
                cam2hdr_dict[total_num] = {}
                cam2hdr_dict[total_num]["name"] = str(total_num).zfill(5)
                cam2hdr_dict[total_num]["camera"] = i
                cam2hdr_dict[total_num]["hdri"] = hdri
                cam2hdr_dict[total_num]["sky"] = sky
                cam2hdr_dict[total_num]["rot"] = rot
                total_num += 1
    # write to json
    save_json(INFO_PATH, cam2hdr_info, cam2hdr_dict)
    return cam2hdr_dict

def add_cameras_from_dict(camera_dict):
    for idx in camera_dict:
        loc = camera_dict[idx]["location"]
        eul = camera_dict[idx]["rotation_euler"]
        # f = camera_dict[idx]["focal"]
        cam = bpy.data.cameras.new("Camera")
        cam_obj = bpy.data.objects.new(cam.name, cam)
        bpy.context.collection.objects.link(cam_obj)
        cam_obj.data.lens = 50.0 #for street view we use 30, for aerial view we use 50
        cam_obj.location[0] = loc[0]
        cam_obj.location[1] = loc[1]
        cam_obj.location[2] = loc[2]
        cam_obj.rotation_euler[0] = eul[0]
        cam_obj.rotation_euler[1] = eul[1]
        cam_obj.rotation_euler[2] = eul[2]

def clear_scene():           
    # clear original cameras
    for l in filter(lambda o: o.type == 'CAMERA', bpy.data.objects):
        bpy.data.objects.remove(l)
        
clear_scene()
setup_rendering('CYCLES', s, 'GPU', rx, ry)

camera_input_file = os.path.join(INFO_PATH, caminput_info)
if os.path.exists(camera_input_file):
    d = load_cameras(camera_input_file)
    add_cameras_from_dict(d)
    streets = None
else:
    streets, cameras_centers, cameras_poses = generate_cameras(cameras_centers, cameras_poses, sb=sb, se=se)
    add_cameras(cameras_centers, cameras_poses, list(range(len(cameras_centers))))

set_objects_num()

# multi-channel rendering
output_nodes = setup_multichannel(path=RENDER_PATH, use_diffuse=True, use_shading=True, only_shading=True, use_object=True, use_normal=True, use_depth=True)

# set_output_path('00000', output_nodes)
# setting sky hdri
all_hdrs = [f for f in os.listdir(hdri_dir) if f.endswith('.exr')]
setup_sky_hdri(hdri_dir)
hdri_dict = set_hdri_list(all_hdrs)

# get all camera objects
record_cameras(streets)
cameras = list(filter(lambda o: o.type == 'CAMERA', bpy.data.objects))
# generate camera-hdri rotation matching list
cam2hdr_dict = record_hdri_camera(len(cameras), len(all_hdrs), cameras)

scene = bpy.context.scene

for i, idx in enumerate(cam2hdr_dict):
    img = cam2hdr_dict[idx]
    cam_index = img["camera"]
    name = img["name"]
    hdri = img["hdri"]
    rot = img["rot"]
    sky = img["sky"]
    bpy.context.scene.camera = cameras[cam_index]
    choose_hdr = hdri_dict[hdri]
    bpy.context.scene.prev = choose_hdr
    bpy.data.worlds["EasyHDR"].node_tree.nodes["Mapping"].inputs[2].default_value[2] = a2r(rot)
    bpy.data.worlds["EasyHDR"].node_tree.nodes["Math_add"].inputs[1].default_value = sky
    render_path = RENDER_PATH + "/"+name
    scene.render.filepath = render_path
    set_output_path(name, output_nodes)
    bpy.ops.render.render( write_still=True )

