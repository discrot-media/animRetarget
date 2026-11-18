import bpy
import copy

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
    "scale": (1,1,1),
}

Mapping_Template = {
    
}

def apply_pose(obj):
    source_arm = obj.retarget_source
    links = obj.retarget_links

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
        apply_pose(context.object)
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
    del bpy.types.Object.retarget_links
    del bpy.types.Object.retarget_source
    bpy.utils.unregister_class(LinkItem)
    
    bpy.utils.unregister_class(AddLink)
    bpy.utils.unregister_class(RemoveLink)
    bpy.utils.unregister_class()

    bpy.utils.unregister_class(LinksPanel)
    bpy.utils.unregister_class(RetargetPanel)
    
    print("Add-on Disabled")
        
if __name__ == "__main__":
    register()