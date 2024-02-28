# Blender Add-on Information
bl_info = {
    "name": "CakeParticles",
    "author": "ScaryPlasmon",
    "description": "Simplifies Baking Particles into Objects",
    "blender": (3, 6, 2),
    "version": (2, 5, 0),
    "location": "ObjectProperties",
    "warning": "",
    "doc_url": "https://sites.google.com/view/cakeparticlesdocs/home-page",
    "tracker_url": "",
    "category": "Physics"
}

import bpy
import bpy.utils.previews

# Converts string to integer if possible
def str_to_int(value):
    return int(value) if value.isdigit() else 0

# Converts string to Blender icon
def str_to_icon(value):
    icons = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
    return icons[value].value if value in icons.keys() else str_to_int(value)

# Converts icon to string representation
def icon_to_str(value):
    for icon in bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items:
        if icon.value == value:
            return icon.name
    return "NONE"

# Converts enum set to string
def enum_set_to_str(value):
    return "[" + ", ".join(list(value)) + "]" if isinstance(value, set) and value else "[]"

# Converts string to specified type with a default fallback
def str_to_type(value, target_type, default_value):
    try:
        return target_type(value)
    except:
        return default_value

# Global variables
addon_keymaps = {}
icons = None
addon_main = {}

#-----Bake Particles-----#

# Keyframe constants
KEYFRAME_LOCATION = True
KEYFRAME_ROTATION = True
KEYFRAME_SCALE = True
KEYFRAME_VISIBILITY = False
KEYFRAME_VISIBILITY_SCALE = True

# # Create objects for each particle
# def create_particle_objects(particle_system, source_objects):
#     created_objects = []

#     particle_collection = bpy.data.collections.new(name="particles")
#     bpy.context.scene.collection.children.link(particle_collection)

#     for index, _ in enumerate(particle_system.particles):
#         object_index = index % len(source_objects)
#         mesh = source_objects[object_index].data
#         duplicate = bpy.data.objects.new(
#             name=f"particle.{index:03d}",
#             object_data=mesh)
#         particle_collection.objects.link(duplicate)
#         created_objects.append(duplicate)

#     return created_objects

# # Match and keyframe objects to particles
# def match_keyframe_objects(particle_system, objects, start_frame, end_frame, step=1):
#     for frame in range(start_frame, end_frame + 1, step):
#         print(f"Frame {frame} processed")
#         print(f"Keyframing at Frame {frame} with Step {step}")
#         bpy.context.scene.frame_set(frame)
#         for particle, obj in zip(particle_system.particles, objects):
#             match_object_to_particle(particle, obj)
#             keyframe_object(obj, frame)




def create_particle_objects(particle_system, source_objects):
    created_objects = []
    armature_obj = None
    meshes_to_duplicate = []

    # Identify the Armature and meshes to duplicate
    for src_obj in source_objects:
        if src_obj.type == 'ARMATURE':
            armature_obj = src_obj
        elif src_obj.type == 'MESH' and src_obj.parent and src_obj.parent.type == 'ARMATURE':
            meshes_to_duplicate.append(src_obj)

    particle_collection = bpy.data.collections.new(name="particles")
    bpy.context.scene.collection.children.link(particle_collection)

    # Only create duplicates if there is an armature
    if armature_obj:
        for index, _ in enumerate(particle_system.particles):
            # Duplicate Armature
            armature_duplicate = armature_obj.copy()
            armature_duplicate.data = armature_obj.data.copy()
            particle_collection.objects.link(armature_duplicate)

            # Duplicate and parent Mesh Objects
            for mesh_obj in meshes_to_duplicate:
                mesh_duplicate = mesh_obj.copy()
                mesh_duplicate.data = mesh_obj.data.copy()
                mesh_duplicate.parent = armature_duplicate
                particle_collection.objects.link(mesh_duplicate)

                # Update Armature modifier to point to the new armature
                for modifier in mesh_duplicate.modifiers:
                    if modifier.type == 'ARMATURE':
                        modifier.object = armature_duplicate

                # Append as a tuple (armature, mesh)
                created_objects.append((armature_duplicate, mesh_duplicate))

    return created_objects

def match_keyframe_objects(particle_system, object_pairs, start_frame, end_frame, step=1):
    particle_count = len(particle_system.particles)

    for frame in range(start_frame, end_frame + 1, step):
        bpy.context.scene.frame_set(frame)
        particle_index = (frame - start_frame) % particle_count  # Wrap around particle index

        for armature, mesh in object_pairs:
            particle = particle_system.particles[particle_index]
            match_object_to_particle(particle, armature)
            keyframe_object(armature, frame)
            keyframe_object(mesh, frame)

# Match object properties to particle
def match_object_to_particle(particle, obj):
    obj.location = particle.location
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = particle.rotation
    visibility = particle.alive_state == 'ALIVE'

    if KEYFRAME_VISIBILITY_SCALE:
        obj.scale = (0.001, 0.001, 0.001) if not visibility else (particle.size,) * 3

    if visibility:
        obj.hide_viewport = False
        obj.hide_render = False

# Add keyframes to object properties at specified frames
def keyframe_object(obj, frame):
    if KEYFRAME_LOCATION:
        obj.keyframe_insert("location", frame=frame)
    if KEYFRAME_ROTATION:
        obj.keyframe_insert("rotation_quaternion", frame=frame)
    if KEYFRAME_SCALE:
        obj.keyframe_insert("scale", frame=frame)
# Remove fake users from a collection
def remove_fake_users(collection_name):
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        print(f"No collection named '{collection_name}' found")
        return

    for obj in collection.objects:
        if obj.data and obj.data.use_fake_user:
            bpy.data.meshes.remove(obj.data, do_unlink=True)
        bpy.data.objects.remove(obj, do_unlink=True)

    bpy.data.collections.remove(collection)

# Useful for DopeSheet Hierarchy animation simplification (outOfScope)
# class SimplifyAnimationOperator(bpy.types.Operator):
#     bl_idname = "object.simplify_animation"
#     bl_label = "Simplify"

#     def execute(self, context):
#         remove_inbetween(context, bpy.context.selected_pose_bones)
#         return {'FINISHED'}

#-----Simplify Animation-----#
    
class SimplifyObjectAnimationOperator(bpy.types.Operator):
    bl_idname = "object.simplify_object_animation"
    bl_label = "Simplify Animation"
    bl_description = """Hover over the timeline to refresh don't spam the button"""

    def execute(self, context):
        remove_inbetween(context, bpy.context.selected_objects)
        return {'FINISHED'}


def remove_inbetween(context, objs):
    step = context.scene.step
    
    for obj in objs:
        if obj.animation_data:  # Check that animation data exists
            action = obj.animation_data.action
            
            if action:  # Check that an action exists
                for fcurve in action.fcurves:
                    keyframe_points = [point for point in fcurve.keyframe_points if point.select_control_point]  # Filter only selected keyframes
                    
                    for i in range(len(keyframe_points) - 1, -1, -1):  # Reverse loop over keyframes
                        if i % step != 0:
                            fcurve.keyframe_points.remove(keyframe_points[i])



# Main function to execute particle baking
def main(bake_step):
    print(f"Bake step received: {bake_step}")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    active_object = bpy.context.object
    evaluated_object = depsgraph.objects[active_object.name]
    source_objects = [obj for obj in bpy.context.selected_objects if obj != active_object]

    for particle_sys in evaluated_object.particle_systems:
        start_frame = bpy.context.scene.frame_start
        end_frame = bpy.context.scene.frame_end
        particle_objects = create_particle_objects(particle_sys, source_objects)
        match_keyframe_objects(particle_sys, particle_objects, start_frame, end_frame, bake_step)

#-----------GUI-----------#
       
# Blender Panel Class for CakeParticles
class CakeParticlesPanel(bpy.types.Panel):
    bl_label = 'CakeParticles(❁´◡`❁)'
    bl_idname = 'CAKE_PT_Particles'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_category = 'CakeParticles'
    bl_order = 0
    bl_options = {'HEADER_LAYOUT_EXPAND'}
    
    bl_ui_units_x = 0

    @classmethod
    def poll(cls, context):
        return True
    
    def draw_header(self, context):
        layout = self.layout
        
    def draw(self, context):
        layout = self.layout
        bake_box = layout.box()
        bake_box.label(text='Select how dense your animation should be', icon='SEQ_LUMA_WAVEFORM')
        
        bake_box.prop(context.window_manager, "cake_bake_step", text="Bake Step")
        bake_box.label(text='Keep the emitter active and the particle objects selected', icon='PIVOT_ACTIVE')
        bake_box.operator('cake.bake_particles', text='Bake', icon='PARTICLE_POINT')

        clear_box = layout.box()
        clear_box.label(text='Clear Previous Bake', icon='CANCEL')
        clear_box.operator('cake.clear_previous_bake', text='Clear', icon='TRASH')

        export_box = layout.box()
        export_box.label(text='Export Options', icon='EXPORT')
        export_box.operator('export_scene.fbx', text='Export as FBX', icon='FILE_TICK').use_selection = True

class BakeParticlesOperator(bpy.types.Operator):
    bl_idname = "cake.bake_particles"
    bl_label = "Bake Particles"
    bl_description = "Bake simulated particles into keyframe animations"
    bl_options = {"REGISTER", "UNDO"}

    bake_step: bpy.props.IntProperty(default=1, min=1, description="Bake every N frames")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        bake_step_value = context.window_manager.cake_bake_step
        print(f"Bake step in execute: {bake_step_value}")  # Debugging statement
        main(bake_step_value)
        return {"FINISHED"}
    
# Operator to clear previous bakes
class ClearPreviousBakeOperator(bpy.types.Operator):
    bl_idname = "cake.clear_previous_bake"
    bl_label = "Clear Previous Bake"
    bl_description = "Remove all objects in the 'particles' collection and their data blocks"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        remove_fake_users("particles")
        self.report({'INFO'}, "Cleared Previous Bake")
        return {"FINISHED"}

class SimplifyAnimationPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_simplify"
    bl_label = "(❁´◡`❁)Reduce Frames"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'

    def draw(self, context):
        layout = self.layout

        if context.scene:
            ks = context.scene.keying_sets_all
            if ks:
                layout.prop_search(context.scene, "keying_set", ks, "name", text="Active Keying Set")
            else:
                layout.label(text="No keying sets found.")
        
        s_box = layout.box()
        s_box.prop(context.scene, 'step', text='Step Size')
        s_box.label(text='Only affects actively selected frames of selected objects', icon='STICKY_UVS_LOC')
        
        row = layout.row()
        # row.operator("object.simplify_animation")
        row.operator("object.simplify_object_animation", icon='BRUSH_CURVES_CUT' )

# Register the Add-on
def register():
    bpy.utils.register_class(CakeParticlesPanel)
    bpy.utils.register_class(BakeParticlesOperator)
    bpy.utils.register_class(ClearPreviousBakeOperator)
    bpy.types.WindowManager.cake_bake_step = bpy.props.IntProperty(
        name="Bake Step",
        default=1,
        min=1,
        description="Wider the Step, less precise the animation."
    )
    bpy.utils.register_class(SimplifyAnimationPanel)
    bpy.utils.register_class(SimplifyObjectAnimationOperator)
    bpy.types.Scene.step = bpy.props.IntProperty(name = "Step Size", default = 1, min=1, description='Larger the Step Bigger the Cut')

# Unregister the Add-on
def unregister():
    bpy.utils.unregister_class(CakeParticlesPanel)
    bpy.utils.unregister_class(BakeParticlesOperator)
    bpy.utils.unregister_class(ClearPreviousBakeOperator)
    del bpy.types.WindowManager.cake_bake_step
    bpy.utils.unregister_class(SimplifyAnimationPanel)
    bpy.utils.unregister_class(SimplifyObjectAnimationOperator)
    del bpy.types.Scene.step

# Required for Blender to recognize the script as an add-on
if __name__ == "__main__":
    register()
