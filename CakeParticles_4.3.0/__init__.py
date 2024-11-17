# Blender Add-on Information
bl_info = {
    "name": "CakeParticles",
    "author": "ScaryPlasmon",
    "description": "Simplifies Baking Particles into Objects",
    "blender": (4, 2, 0),
    "version": (4, 3, 0),
    "location": "ObjectProperties",
    "warning": "",
    "doc_url": "https://github.com/Scaryplasmon/CakeParticles",
    "tracker_url": "",
    "category": "Physics"
}

import bpy
import bpy.utils.previews
import random
import colorsys

# Global variables
addon_keymaps = {}
addon_main = {}

# Keyframe constants
KEYFRAME_LOCATION = True
KEYFRAME_ROTATION = True
KEYFRAME_SCALE = True
#You don´t wanna change these values
KEYFRAME_VISIBILITY = False
KEYFRAME_VISIBILITY_SCALE = True


def create_or_clear_collection(collection_name):
    """Create a new collection or clear existing one if it exists"""
    existing_collection = bpy.data.collections.get(collection_name)
    
    if existing_collection:
        # Remove all objects from the collection
        for obj in existing_collection.objects:
            if obj.data and obj.data.use_fake_user:
                bpy.data.meshes.remove(obj.data, do_unlink=True)
            bpy.data.objects.remove(obj, do_unlink=True)
        return existing_collection
    else:
        # Create new collection
        new_collection = bpy.data.collections.new(name=collection_name)
        bpy.context.scene.collection.children.link(new_collection)
        return new_collection

def create_particle_objects(particle_system, source_objects, collection_name):
    if not source_objects:
        raise Exception("No source objects available to create particle instances.")

    created_objects = []
    
    # Generate a random color for the collection
    n=random.randint(1,8)
    color_code=f'COLOR_0{n}'
    # Create or get the collection
    particle_collection = create_or_clear_collection(collection_name)
    particle_collection.color_tag = color_code

    for index, _ in enumerate(particle_system.particles):
        object_index = index % len(source_objects)
        mesh = source_objects[object_index].data
        duplicate = bpy.data.objects.new(
            name=f"particle.{index:03d}",
            object_data=mesh)
        particle_collection.objects.link(duplicate)
        if duplicate.animation_data:
            duplicate.animation_data_clear()
        created_objects.append(duplicate)

    return created_objects

def match_keyframe_objects(particle_system, objects, start_frame, end_frame, step=1):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    for frame in range(start_frame, end_frame + 1, step):
        # print(f"\nProcessing Frame {frame}")
        # Set the frame and update the dependency graph
        bpy.context.scene.frame_set(frame)
        depsgraph.update()
        
        # Get the evaluated particle system for this frame
        eval_obj = particle_system.id_data.evaluated_get(depsgraph)
        eval_psys = eval_obj.particle_systems[particle_system.name]
        
        for i, (particle, obj) in enumerate(zip(eval_psys.particles, objects)):
            # print(f"\nParticle {i} at frame {frame}:")
            match_object_to_particle(particle, obj, frame)
            keyframe_object(obj, frame)

def match_object_to_particle(particle, obj, frame):
    # # Store previous rotation for debugging
    # prev_rot = obj.rotation_quaternion.copy() if obj.rotation_mode == 'QUATERNION' else None
    
    # Update location
    obj.location = particle.location
    
    obj.rotation_mode = 'QUATERNION'

    if hasattr(particle, 'matrix'):
        rot_matrix = particle.matrix.to_3x3()
        obj.rotation_quaternion = rot_matrix.to_quaternion()
    elif hasattr(particle, 'rotation_matrix'):
        rot_matrix = particle.rotation_matrix
        obj.rotation_quaternion = rot_matrix.to_quaternion()
    else:
        obj.rotation_quaternion = particle.rotation
    
    visibility = particle.alive_state == 'ALIVE'
    if KEYFRAME_VISIBILITY_SCALE:
        obj.scale = (0.0001, 0.0001, 0.0001) if not visibility else (particle.size,) * 3

    if visibility:
        obj.hide_viewport = False
        obj.hide_render = False

def keyframe_object(obj, frame):
    if KEYFRAME_LOCATION:
        obj.keyframe_insert("location", frame=frame)
    if KEYFRAME_ROTATION:
        obj.keyframe_insert("rotation_quaternion", frame=frame)
    if KEYFRAME_SCALE:
        obj.keyframe_insert("scale", frame=frame)
    
    # Ensure proper interpolation for rotations
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            if fcurve.data_path == "rotation_quaternion":
                for keyf in fcurve.keyframe_points:
                    keyf.interpolation = 'LINEAR'

def remove_inbetween(context, objs):
    step = context.scene.step
    
    for obj in objs:
        if obj.animation_data: 
            action = obj.animation_data.action
            
            if action:
                for fcurve in action.fcurves:
                    keyframe_points = [point for point in fcurve.keyframe_points if point.select_control_point]
                    
                    for i in range(len(keyframe_points) - 1, -1, -1):
                        if i % step != 0:
                            fcurve.keyframe_points.remove(keyframe_points[i])
# Main function to execute particle baking
def main(context, source_objects):
    bake_step = context.scene.bake_step
    depsgraph = bpy.context.evaluated_depsgraph_get()
    active_object = bpy.context.object
    evaluated_object = depsgraph.objects[active_object.name]
    for particle_sys in evaluated_object.particle_systems:
        start_frame = bpy.context.scene.frame_start
        end_frame = bpy.context.scene.frame_end
        particle_objects = create_particle_objects(particle_sys, source_objects)
        match_keyframe_objects(particle_sys, particle_objects, start_frame, end_frame, bake_step)

# ------(❁´◡`❁)-------
# Class and function definitions for UI and Blender registration follow...
# ------(❁´◡`❁)-------

# Blender Panel Class for CakeParticles
class CakeParticlesPanel(bpy.types.Panel):
    bl_label = 'CakeParticles(❁´◡`❁)'
    bl_idname = 'CAKE_PT_Particles'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_category = 'CakeParticles'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.object is not None
    
    def draw(self, context):
        layout = self.layout
        # Main controls
        col = layout.column(align=True)
        col.prop(context.scene, "target_collection_name", text="Collection Name", icon='OUTLINER_COLLECTION')
        col.prop(context.scene, "bake_step", text="bake-step")
        col.operator('cake.bake_particles', text='Bake', icon='EXPERIMENTAL')
        
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "show_info", 
                icon='TRIA_DOWN' if context.scene.show_info else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Basic Information")
        
        if context.scene.show_info:
            col = box.column()
            col.label(text='Baking range = timeline range', icon='MOD_TIME')
            col.label(text='Keep the emitter Active', icon='OBJECT_DATA')
            col.label(text='Keep the Objects to instance Selected', icon='POINTCLOUD_DATA')
            col.label(text='Adjust bake step to change keyframing interval, animation density', icon='ACTION')
        
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "show_advanced", 
                icon='TRIA_DOWN' if context.scene.show_advanced else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Advanced Tips")
        
        if context.scene.show_advanced:
            col = box.column()
            col.label(text='keyframes particles location, rotation, scale and visibility', icon='RNA')
            col.label(text='if particles don´t rotate make sure to set Dynamic=True->(use_dynamic_rotation)-[emitter particles properties tab]', icon='ORIENTATION_GIMBAL')
            col.label(text='particle dies and spawn at 0.0 scale to facilitate exports', icon='GHOST_DISABLED')
            col.label(text='support: MESH, GREASE_PENCIL, METABALLS, FORCE FIELDS, CAMERAS ++', icon='OBJECT_DATA')
            col.label(text='Press N in the timeline to find the Edit panel, for animation post processing', icon='WINDOW')

class SimplifyAnimationPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_simplify"
    bl_label = "(❁´◡`❁)EDIT(❁´◡`❁)"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        
        # Main controls
        col = layout.column(align=True)
        col.prop(context.scene, 'step', text='step size')
        col.operator("object.simplify_object_animation")
        
        col = layout.column(align=True)
        col.prop(context.scene, 'scale_range', text="Random Range")
        col.operator('object.scale_keyframes', text='Randomize Times', icon='RNA')
        
        # Edit info panel
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "show_edit_info", 
                icon='TRIA_DOWN' if context.scene.show_edit_info else 'TRIA_RIGHT',
                icon_only=True, emboss=False)
        row.label(text="Edit Information")
        
        if context.scene.show_edit_info:
            col = box.column()
            col.label(text='Larger Step = Bigger Cut', icon='PARTICLEMODE')
            col.label(text='Only affects selected frames', icon='STICKY_UVS_LOC')
            col.label(text="Hover or click over the timeline to refresh don't spam the button", icon='INFO')

class BakeParticlesOperator(bpy.types.Operator):
    bl_idname = "cake.bake_particles"
    bl_label = "Bake Particles"
    bl_description = "Bake particles motion into keyframed animations"
    bl_options = {"REGISTER", "UNDO"}

    def validate_particle_settings(self, context):
        obj = context.active_object
        if not obj or not obj.particle_systems.active:
            return "No active particle system found"
            
        psys = obj.particle_systems.active
        settings = psys.settings
        
        warnings = []
        if not settings.use_rotations:
            warnings.append("Particle rotations are not enabled")
            
        return warnings

    def invoke(self, context, event):
        # Check particle settings but only show as info
        warnings = self.validate_particle_settings(context)
        if isinstance(warnings, str):  # If it's a string, it's the "no particle system" error
            self.report({'ERROR'}, warnings)
            return {'CANCELLED'}
        elif warnings:  # If there are warnings, show them but continue
            self.report({'INFO'}, "Note: " + " | ".join(warnings))
        
        # Then check if collection exists
        collection_name = context.scene.target_collection_name
        if bpy.data.collections.get(collection_name):
            return context.window_manager.invoke_confirm(
                self, 
                event,
                message=f"Collection '{collection_name}' already exists. Do you want to overwrite it?"
            )
        return self.execute(context)

    def execute(self, context):
        try:
            collection_name = context.scene.target_collection_name
            if not collection_name:
                self.report({'ERROR'}, "Please specify a collection name.")
                return {'CANCELLED'}

            bake_step = context.scene.bake_step
            depsgraph = bpy.context.evaluated_depsgraph_get()
            active_object = bpy.context.object
            evaluated_object = depsgraph.objects[active_object.name]
            source_objects = [obj for obj in bpy.context.selected_objects if obj != active_object]

            if not source_objects:
                self.report({'ERROR'}, "No source objects selected as particle instances.")
                return {'CANCELLED'}

            # Modified main function call with collection name
            for particle_sys in evaluated_object.particle_systems:
                start_frame = bpy.context.scene.frame_start
                end_frame = bpy.context.scene.frame_end
                particle_objects = create_particle_objects(particle_sys, source_objects, collection_name)
                match_keyframe_objects(particle_sys, particle_objects, start_frame, end_frame, bake_step)

            self.report({'INFO'}, f"Successfully baked particles to collection: {collection_name}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error during baking: {str(e)}")
            return {'CANCELLED'}
        return {"FINISHED"}
    
class CollectionCheckOperator(bpy.types.Operator):
    bl_idname = "cake.check_collection"
    bl_label = "Check Collection"
    bl_description = "Check if collection exists and confirm overwrite"
    
    def execute(self, context):
        collection_name = context.scene.target_collection_name
        existing_collection = bpy.data.collections.get(collection_name)
        
        if existing_collection:
            self.report({'WARNING'}, f"Collection '{collection_name}' exists. Use 'Bake' to overwrite.")
        else:
            self.report({'INFO'}, f"Collection '{collection_name}' is available.")
        
        return {'FINISHED'}
    
class SimplifyObjectAnimationOperator(bpy.types.Operator):
    bl_idname = "object.simplify_object_animation"
    bl_label = "Simplify Animation"
    bl_description = "Remove in-between keyframes from the selected objects' animations"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        remove_inbetween(context, bpy.context.selected_objects)
        return {'FINISHED'}
    
class ScaleKeyframesOperator(bpy.types.Operator):
    bl_idname = "object.scale_keyframes"
    bl_label = "Scale Keyframes"
    bl_description = "Scale the keyframes' timelines or TimeOffset modifier of selected objects by a random factor"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        range_value = context.scene.scale_range
        scaled_count = 0

        for obj in bpy.context.selected_objects:
            if obj.type == 'GPENCIL':  # Automatically detect if object is grease pencil
                time_offset_mod = None
                for mod in obj.grease_pencil_modifiers:
                    if mod.type == 'GP_TIME':
                        time_offset_mod = mod
                        break

                if not time_offset_mod:
                    time_offset_mod = obj.grease_pencil_modifiers.new(name="TimeOffset", type='GP_TIME')
                
                random_scale_factor = 1 + random.uniform(-range_value, range_value)
                time_offset_mod.frame_scale *= random_scale_factor
                obj.update_tag()
                scaled_count += 1
            elif obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                random_scale_factor = 1 + random.uniform(-range_value, range_value)
                
                for fcurve in action.fcurves:
                    for keyframe in fcurve.keyframe_points:
                        keyframe.co.x *= random_scale_factor
                        keyframe.handle_left.x *= random_scale_factor
                        keyframe.handle_right.x *= random_scale_factor
                    fcurve.update()
                scaled_count += 1

        if scaled_count > 0:
            self.report({'INFO'}, f"Scaled {scaled_count} objects' timelines by random factors within range: ±{range_value}")
        else:
            self.report({'WARNING'}, "No objects with animation data selected")
        return {'FINISHED'}

# Register the Add-on
def register():
    bpy.utils.register_class(CakeParticlesPanel)
    bpy.utils.register_class(BakeParticlesOperator)
    bpy.utils.register_class(CollectionCheckOperator)
    bpy.types.Scene.target_collection_name = bpy.props.StringProperty(
        name="Target Collection",
        default="particles",
        description="Name of the collection to store baked particles"
    )
    
    bpy.types.Scene.bake_step = bpy.props.IntProperty(
        name="Bake Step",
        default=1,
        min=1,
        description="Keyframe every N frames"
    )
    bpy.utils.register_class(SimplifyAnimationPanel)
    bpy.utils.register_class(SimplifyObjectAnimationOperator)
    bpy.types.Scene.step = bpy.props.IntProperty(
        name = "Step Size", 
        default = 1,
        min=1,
        description="step size = minimum distance between selected frames after processing"
        )
    bpy.utils.register_class(ScaleKeyframesOperator)
    
    bpy.types.Scene.scale_range = bpy.props.FloatProperty(
        name="Scale Range",
        default=0.5,
        min=0.0,
        description="Range within which to randomly scale the keyframes"
    )
    bpy.types.Scene.show_info = bpy.props.BoolProperty(
        default=False,
        name="Show Basic Information"
    )
    bpy.types.Scene.show_advanced = bpy.props.BoolProperty(
        default=False,
        name="Show Advanced Tips"
    )
    bpy.types.Scene.show_edit_info = bpy.props.BoolProperty(
        default=False,
        name="Show Edit Information"
    )

# Unregister the Add-on
def unregister():
    bpy.utils.unregister_class(CakeParticlesPanel)
    bpy.utils.unregister_class(BakeParticlesOperator)
    bpy.utils.unregister_class(CollectionCheckOperator)
    
    del bpy.types.Scene.target_collection_name
    del bpy.types.Scene.bake_step
    bpy.utils.unregister_class(SimplifyAnimationPanel)
    bpy.utils.unregister_class(SimplifyObjectAnimationOperator)
    del bpy.types.Scene.step
    bpy.utils.unregister_class(ScaleKeyframesOperator)
    del bpy.types.Scene.scale_range
    del bpy.types.Scene.show_info
    del bpy.types.Scene.show_advanced
    del bpy.types.Scene.show_edit_info

# Required for Blender to recognize the script as an add-on
if __name__ == "__main__":
    register()
