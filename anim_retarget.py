import bpy
import copy
from mathutils import Vector, Matrix, Quaternion

bl_info = {
    "name": "Simple Anim Retarget",
    "blender": (2, 80, 0),
    "author": "Discrot",
    "version": (0,1,0),
    "category": "Object",
}

##### main logic

Bone_Template = {
    "name": "",
    "position": (0,0,0),
    "rotation": (1,0,0,0),
    "forward": (0,0,0),
    "up": (0,0,0),
    "scale": (1,1,1),
}

Link_Template = {
    "source": copy.deepcopy(Bone_Template),
    "target": copy.deepcopy(Bone_Template),
    "roll": 0.0,
    "apply": {"pos": False, "rot": True, "scale": False},
    "world": {"pos": False, "rot": True},
}

Mapping_Template = {
    "source_armature": "",
    "target_armature": "",
    "links": [],
}

def make_mapping(obj):
    source = obj.retarget_source
    links = obj.retarget_links
    
    mapping = copy.deepcopy(Mapping_Template)
    mapping["source_armature"] = source.name
    mapping["target_armature"] = obj.name
    
    for elem in links:
        
        if elem.target_bone not in obj.data.bones or elem.source_bone not in source.pose.bones:
            continue
        # source bone: source.pose.bones[elem.source_bone]
        # target bone: obj.pose.bones[elem.target_bone]
        
        src_bone_dict = copy.deepcopy(Bone_Template)
        src_bone_pose = source.pose.bones[elem.source_bone]
        
        src_bone_dict.update(
            name = elem.source_bone,
            position = tuple(src_bone_pose.matrix.translation) if elem.world_pos else tuple(src_bone_pose.location),
            rotation = tuple(src_bone_pose.matrix_basis.to_quaternion()),
            forward = tuple(src_bone_pose.matrix.to_3x3().col[1]),
            up = tuple(src_bone_pose.matrix.to_3x3().col[2]),
            scale = tuple(src_bone_pose.scale),
        )
        
        trg_bone_dict = copy.deepcopy(Bone_Template)
        trg_bone_pose = obj.pose.bones[elem.target_bone]
        
        trg_bone_dict.update(
            name = elem.target_bone,
            position = tuple(trg_bone_pose.location),
            rotation = tuple(trg_bone_pose.matrix_basis.to_quaternion()),
            forward = tuple(trg_bone_pose.matrix.to_3x3().col[1]),
            up = tuple(trg_bone_pose.matrix.to_3x3().col[2]),
            scale = tuple(trg_bone_pose.scale),
        )
        
        link = copy.deepcopy(Link_Template)
        link.update(
            source = src_bone_dict,
            target = trg_bone_dict,
            roll = elem.roll,
            apply = dict(pos=elem.apply_pos, rot=elem.apply_rot, scale=elem.apply_scale),
            world = dict(pos=elem.world_pos, rot=elem.world_rot),
        )
        
        mapping["links"].append(link)
    
    mapping["links"].sort(key=lambda l: len(obj.data.bones[l["target"]["name"]].parent_recursive))
    
    return mapping

def calculate_pose(mapping):
    for link in mapping["links"]:
        src = link["source"]
        trg = link["target"]

        if link["apply"]["pos"]:
            trg["position"] = src["position"]

        if link["apply"]["rot"]:
            if link["world"]["rot"]:
                trg["forward"] = src["forward"]
                trg["up"] = src["up"]
            else:
                trg["rotation"] = src["rotation"]

        if link["apply"]["scale"]:
            trg["scale"] = src["scale"]

def build_rotation_matrix(forward, up, roll):
    y = Vector(forward).normalized()
    z = Vector(up).normalized()
    z = Quaternion(y, roll) @ z 
    x = y.cross(z).normalized()
    z = x.cross(y)       
    return Matrix((x, y, z)).transposed().to_4x4()            

def apply_pose(mapping):
    
    target = bpy.data.objects[mapping["target_armature"]]

    for link in mapping["links"]:
        trg = link["target"]
        trg_bone_pose = target.pose.bones[trg["name"]]
        old_scale = tuple(trg_bone_pose.scale)

        world_pos = link["apply"]["pos"] and link["world"]["pos"]
        world_rot = link["apply"]["rot"] and link["world"]["rot"]
        
        if world_pos or world_rot:
            matrix = trg_bone_pose.matrix.copy()

            if world_rot:
                translation = matrix.translation.copy()
                matrix = build_rotation_matrix(trg["forward"], trg["up"], link["roll"])
                matrix.translation = translation

            if world_pos:
                matrix.translation = trg["position"]

            trg_bone_pose.matrix = matrix
            
        if link["apply"]["pos"] and not link["world"]["pos"]:
            trg_bone_pose.location = trg["position"]

        if link["apply"]["rot"] and not link["world"]["rot"]:
            if trg_bone_pose.rotation_mode == 'QUATERNION':
                trg_bone_pose.rotation_quaternion = trg["rotation"]
            elif trg_bone_pose.rotation_mode != 'AXIS_ANGLE':
                trg_bone_pose.rotation_euler = Quaternion(trg["rotation"]).to_euler(trg_bone_pose.rotation_mode)

        trg_bone_pose.scale = trg["scale"] if link["apply"]["scale"] else old_scale
        bpy.context.view_layer.update()
    

##### blender UI drawing

# links

class LinkItem(bpy.types.PropertyGroup):
    source_bone: bpy.props.StringProperty(name="Source Bone")
    target_bone: bpy.props.StringProperty(name="Target Bone")    
    
    apply_pos: bpy.props.BoolProperty(name="Position", default=False)
    apply_rot: bpy.props.BoolProperty(name="Rotation", default=True)
    apply_scale: bpy.props.BoolProperty(name="Scale", default=False)

    world_pos: bpy.props.BoolProperty(
        name="W.S Position", default = False)
    world_rot: bpy.props.BoolProperty(
        name="W.S Rotation", default = True)
        
    roll: bpy.props.FloatProperty(name="Bone Roll", subtype='ANGLE')
    
class AddLink(bpy.types.Operator):
    bl_idname = "retarget.add_link"
    bl_label = "Add Link"

    def execute(self, context):
        context.object.retarget_links.add()
        return {'FINISHED'}
        
class RemoveLink(bpy.types.Operator):
    bl_idname = "retarget.remove_link"
    bl_label = "Remove Link"

    index: bpy.props.IntProperty()

    def execute(self, context):
        context.object.retarget_links.remove(self.index)
        return {'FINISHED'}
    
class LinksPanel(bpy.types.Panel):
    bl_label = "Mapping"
    bl_idname = "DATA_PT_anim_retarget_links"
    bl_parent_id = "DATA_PT_anim_retarget"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"
    
    def draw(self, context):
        
        obj = context.object
        source = obj.retarget_source
        
        if source:
            for i, link in enumerate(obj.retarget_links):
                box = self.layout.box()

                row = box.row()
                row.prop_search(link, "source_bone", source.pose, "bones")
                row.prop_search(link, "target_bone", obj.pose, "bones")
                
                rmv = row.operator("retarget.remove_link", text="", icon='X')
                rmv.index = i
                
                grid = box.column()
                grid.label(text="Apply Transforms")
                row = grid.row(align=True)
                row.prop(link, "apply_pos", toggle=True)
                row.prop(link, "apply_rot", toggle=True)
                row.prop(link, "apply_scale", toggle=True)

                grid.label(text="Use World Space")
                row = grid.row(align=True)
                row.prop(link, "world_pos", toggle=True, text="Position")
                row.prop(link, "world_rot", toggle=True, text="Rotation")

                box.prop(link, "roll")

            self.layout.operator("retarget.add_link")
            
## debug

class PreviewPose(bpy.types.Operator):
    bl_idname = "retarget.preview_pose"
    bl_label = "Preview Pose"

    def execute(self, context):
        mapping = make_mapping(context.object)
        calculate_pose(mapping)
        apply_pose(mapping)
        return {'FINISHED'}
            
# main panel

class RetargetPanel(bpy.types.Panel):
    bl_label = "Simple Anim Retarget"
    bl_idname = "DATA_PT_anim_retarget"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"
    
    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == 'ARMATURE'

    def draw(self, context):
        obj = context.object
        source = obj.retarget_source
        self.layout.prop(context.object, "retarget_source")
        if source:
            self.layout.operator("retarget.preview_pose")
        
##### blender addon registration

def register():
    bpy.types.Object.retarget_source = bpy.props.PointerProperty(
        name="Source Armature",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE' and obj != self,
    )
    
    bpy.utils.register_class(LinkItem)
    bpy.types.Object.retarget_links = bpy.props.CollectionProperty(type=LinkItem)
    
    bpy.utils.register_class(AddLink)
    bpy.utils.register_class(RemoveLink)
    bpy.utils.register_class(PreviewPose)
    
    bpy.utils.register_class(RetargetPanel)
    bpy.utils.register_class(LinksPanel)
    print("Add-on succesfully enabled")
        
def unregister():
    bpy.utils.unregister_class(LinksPanel)
    
    bpy.utils.unregister_class(AddLink)
    bpy.utils.unregister_class(RemoveLink)
    bpy.utils.unregister_class(PreviewPanel)
    
    bpy.utils.unregister_class(RetargetPanel)
    
    del bpy.types.Object.retarget_links
    del bpy.types.Object.retarget_source
    bpy.utils.unregister_class(LinkItem)
    
    print("Add-on Disabled")
        
if __name__ == "__main__":
    register()