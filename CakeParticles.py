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
import bmesh
from mathutils import Vector

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

def match_keyframe_objects(particle_system, objects, start_frame, end_frame, step=1, keyframe_offset=0):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    for frame_iter_for_particles in range(start_frame, end_frame + 1, step):
        bpy.context.scene.frame_set(frame_iter_for_particles) 
        
        frame_for_keyframes = frame_iter_for_particles + keyframe_offset

        eval_emitter_obj = particle_system.id_data.evaluated_get(depsgraph)
        eval_psys = None
        if eval_emitter_obj:
            eval_psys = eval_emitter_obj.particle_systems.get(particle_system.name)

        particles_on_frame = []
        if eval_psys:
            particles_on_frame = list(eval_psys.particles)
        
        for i, obj in enumerate(objects):
            if i < len(particles_on_frame):
                particle = particles_on_frame[i]
                match_object_to_particle(particle, obj, frame_iter_for_particles) 
            else:
                obj.scale = (0.001, 0.001, 0.001)
                if KEYFRAME_VISIBILITY_SCALE is False and KEYFRAME_VISIBILITY is True:
                    obj.hide_viewport = True
                    obj.hide_render = True
            
            keyframe_object(obj, frame_for_keyframes)

def match_object_to_particle(particle, obj, frame):

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
        obj.scale = (0.001, 0.001, 0.001) if not visibility else (particle.size,) * 3

    if visibility:
        obj.hide_viewport = False
        obj.hide_render = False

def get_directionally_matched_pieces(source_obj_center, all_pieces, particle_system_data, eval_frame, context):
    """
    Attempts to match pieces to particles based on direction.
    Returns a list of pieces ordered to match particle animation tracks.
    """
    if not all_pieces or not particle_system_data:
        return []

    depsgraph = context.evaluated_depsgraph_get()
    bpy.context.scene.frame_set(eval_frame)

    eval_emitter_obj = particle_system_data.id_data.evaluated_get(depsgraph)
    eval_psys = None
    if eval_emitter_obj:
        eval_psys = eval_emitter_obj.particle_systems.get(particle_system_data.name)

    if not eval_psys or not eval_psys.particles:
        return all_pieces[:len(eval_psys.particles)] if eval_psys else all_pieces

    particle_infos = []
    for i, p in enumerate(eval_psys.particles):
        if p.alive_state == 'ALIVE' and hasattr(p, 'velocity'):
            direction = p.velocity.normalized() if p.velocity.length > 0.001 else (p.location - source_obj_center).normalized()
            if direction.length < 0.001 : direction = Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-1,1))).normalized()
            particle_infos.append({'id': i, 'vector': direction, 'original_particle': p, 'used': False})

    piece_infos = []
    for i, piece_obj in enumerate(all_pieces):

        piece_center_world = piece_obj.matrix_world.translation
        outward_vector = (piece_center_world - source_obj_center).normalized()
        if outward_vector.length < 0.001: outward_vector = Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-1,1))).normalized()
        piece_infos.append({'id': i, 'vector': outward_vector, 'object': piece_obj})
    
    if not particle_infos:
        return all_pieces[:0]

    num_slots_to_fill = min(len(particle_infos), len(piece_infos), particle_system_data.settings.count)
    
    ordered_pieces_for_animation = [None] * num_slots_to_fill
 
    
    available_pieces = list(piece_infos)
    assignments = {}

    particle_infos.sort(key=lambda p_info: p_info['id'])

    for p_info in particle_infos:
        if not available_pieces: break
        best_piece_info = None
        highest_dot = -2.0

        for piece_idx, pc_info in enumerate(available_pieces):
            dot = p_info['vector'].dot(pc_info['vector'])
            if dot > highest_dot:
                highest_dot = dot
                best_piece_info = pc_info
                best_piece_list_idx = piece_idx
        
        if best_piece_info:
            assignments[p_info['id']] = best_piece_info['id']
            available_pieces.pop(best_piece_list_idx)
            p_info['used'] = True


    final_ordered_pieces = [None] * particle_system_data.settings.count 
    
    piece_obj_to_id_map = {p['object']: p['id'] for p in piece_infos}

    potential_matches = []
    temp_particles = [p for p in eval_psys.particles]

    for pc_info in piece_infos:
        for particle_idx, p_sys_particle in enumerate(temp_particles):
            if particle_idx >= particle_system_data.settings.count: break

            p_velocity = p_sys_particle.velocity.normalized() if hasattr(p_sys_particle, 'velocity') and p_sys_particle.velocity.length > 0.001 else (p_sys_particle.location - source_obj_center).normalized()
            if p_velocity.length < 0.001 : p_velocity = Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-1,1))).normalized()

            dot = pc_info['vector'].dot(p_velocity)
            potential_matches.append({'dot': dot, 'piece_obj': pc_info['object'], 'particle_idx': particle_idx})

    potential_matches.sort(key=lambda x: x['dot'], reverse=True)
    
    assigned_particles = [False] * particle_system_data.settings.count
    assigned_pieces_set = set()

    for match in potential_matches:
        p_idx = match['particle_idx']
        pc_obj = match['piece_obj']

        if not assigned_particles[p_idx] and pc_obj not in assigned_pieces_set:
            final_ordered_pieces[p_idx] = pc_obj
            assigned_particles[p_idx] = True
            assigned_pieces_set.add(pc_obj)
            if len(assigned_pieces_set) >= len(all_pieces): break
            if sum(assigned_particles) >= particle_system_data.settings.count : break

    
    result_pieces = [None] * min(len(all_pieces), particle_system_data.settings.count)
    
    assigned_particles_indices = set()
    assigned_piece_objects = set()

    for p_slot_idx in range(len(result_pieces)):
        best_match_for_this_slot = None
        best_dot_for_this_slot = -2.0

        if p_slot_idx >= len(temp_particles): continue

        current_particle = temp_particles[p_slot_idx]
        p_vec = current_particle.velocity.normalized() if hasattr(current_particle, 'velocity') and current_particle.velocity.length > 0.001 else (current_particle.location - source_obj_center).normalized()
        if p_vec.length < 0.001 : p_vec = Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-1,1))).normalized()

        best_piece_for_this_particle = None

        for piece_obj in all_pieces:
            if piece_obj in assigned_piece_objects:
                continue

            piece_center_w = piece_obj.matrix_world.translation
            pc_vec = (piece_center_w - source_obj_center).normalized()
            if pc_vec.length < 0.001: pc_vec = Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-1,1))).normalized()

            dot = p_vec.dot(pc_vec)
            if dot > best_dot_for_this_slot:
                best_dot_for_this_slot = dot
                best_piece_for_this_particle = piece_obj
        
        if best_piece_for_this_particle:
            result_pieces[p_slot_idx] = best_piece_for_this_particle
            assigned_piece_objects.add(best_piece_for_this_particle)

    actual_pieces_to_animate = [p for p in result_pieces if p is not None]
    
    if len(actual_pieces_to_animate) < len(result_pieces):
        remaining_pieces = [p for p in all_pieces if p not in assigned_piece_objects]
        fill_idx = 0
        for i in range(len(result_pieces)):
            if result_pieces[i] is None and fill_idx < len(remaining_pieces):
                result_pieces[i] = remaining_pieces[fill_idx]
                assigned_piece_objects.add(remaining_pieces[fill_idx])
                fill_idx += 1
        actual_pieces_to_animate = [p for p in result_pieces if p is not None]


    bpy.context.scene.frame_set(context.scene.frame_current)
    return actual_pieces_to_animate

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
        scene = context.scene
        col = layout.column(align=True)
        col.prop(context.scene, "target_collection_name", text="Collection Name", icon='OUTLINER_COLLECTION')
        col.prop(context.scene, "bake_step", text="bake-step")
        col.operator('cake.bake_particles', text='Bake', icon='EXPERIMENTAL')
        
        box_explode = layout.box()
        row_explode_header = box_explode.row()
        row_explode_header.prop(scene, "show_cake_explosion_options",
                                icon='TRIA_DOWN' if scene.show_cake_explosion_options else 'TRIA_RIGHT',
                                icon_only=True, emboss=False)
        
        row_explode_header.label(text="Cake Explosion 🍰💥")

        if scene.show_cake_explosion_options:
            col_explode_content = box_explode.column(align=True)
            col_explode_content.prop(scene, "cake_explosion_num_cuts")
            col_explode_content.prop(scene, "cake_explosion_split_mode", text="Split Mode")
            col_explode_content.prop(scene, "cake_explosion_seed")
            col_explode_content.prop(scene, "target_collection_name", text="Output Collection")
            
            col_explode_content.separator()
            col_explode_content.label(text="Explosion Animation Settings:")
            row_anim = col_explode_content.row(align=True)
            row_anim.prop(scene, "cake_explosion_emit_frame_start", text="Emit Start")
            row_anim.prop(scene, "cake_explosion_emit_duration", text="Duration")
            col_explode_content.prop(scene, "cake_explosion_velocity", text="Velocity")
            
            col_explode_content.separator()
            col_explode_content.label(text=f"Bake Range: {scene.frame_start}-{scene.frame_end} (Scene Range)")
            col_explode_content.label(text=f"Bake Step: {scene.bake_step} (Scene Bake Step)")
            col_explode_content.operator(CAKE_OT_AdjustExplosionParticles.bl_idname, text="Set Explosion Settings", icon='MOD_PARTICLES')
            col_explode_content.operator(CAKE_OT_CakeExplosion.bl_idname, text="Explode 🍰💥", icon='MOD_EXPLODE')
        
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


# ------(❁´◡`❁)-------
# Operators classes which control the executions
# ------(❁´◡`❁)-------

class CAKE_OT_CakeExplosion(bpy.types.Operator):
    """Splits selected mesh into target pieces by creating temporary seams for each piece, 
       then animates them using its active particle system, with an initial state display."""
    bl_idname = "cake.cake_explosion"
    bl_label = "Prepare & Explode Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        scene = context.scene
        if not obj or obj.type != 'MESH' or not obj.particle_systems.active:
            return False
        if not scene.target_collection_name.strip():
            cls.poll_message_set("Target Collection Name must be set in CakeParticles panel.")
            return False
        return True

    def _get_bmesh_bounds(self, bm_elements):
        """Helper to get bounding box of a list of BMesh elements (verts, or faces from which verts are derived)."""
        if not bm_elements:
            return None, None

        coords = []
        if all(isinstance(elem, bmesh.types.BMVert) for elem in bm_elements):
            coords = [v.co.copy() for v in bm_elements if v.is_valid]
        elif all(isinstance(elem, bmesh.types.BMFace) for elem in bm_elements):
            for f in bm_elements:
                if f.is_valid:
                    coords.extend(v.co.copy() for v in f.verts)
        
        if not coords:
            return None, None

        min_co = Vector((min(c[0] for c in coords), min(c[1] for c in coords), min(c[2] for c in coords)))
        max_co = Vector((max(c[0] for c in coords), max(c[1] for c in coords), max(c[2] for c in coords)))
        return min_co, max_co
    

    def _chip_one_piece(self, bm, context, num_bisections_on_chunk, iteration_info_for_debug=""):
        """
        Applies 'num_bisections_on_chunk' to the current bm, marks seams,
        then selects and returns True if a PARTIAL island was selected.
        Used by NON_UNIFORM and RANDOM_CHIPPING modes.
        """
        if not bm.faces or not any(f.is_valid for f in bm.faces):
            self.report({'DEBUG'}, f"Debug (_chip_one_piece): No valid faces in BMesh for {iteration_info_for_debug}.")
            return False

        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        for _ in range(num_bisections_on_chunk):
            current_valid_verts = [v for v in bm.verts if v.is_valid]
            if not current_valid_verts or not any(f.is_valid for f in bm.faces): break

            min_co, max_co = self._get_bmesh_bounds(current_valid_verts)
            if min_co is None: continue
            
            dims = (max_co - min_co) / 2.0
            center = min_co + dims
            safe_dims = Vector([max(abs(d), 0.001) for d in dims])
            
            plane_co = center + Vector((random.uniform(-safe_dims.x, safe_dims.x),
                                        random.uniform(-safe_dims.y, safe_dims.y),
                                        random.uniform(-safe_dims.z, safe_dims.z)))
            plane_no = Vector((random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0)))
            
            if plane_no.length < 0.0001: plane_no = Vector((1.0,0.0,0.0))
            plane_no.normalize()

            try:
                geom_to_bisect = [e for e in bm.verts[:] + bm.edges[:] + bm.faces[:] if e.is_valid]
                if not geom_to_bisect or not any(f.is_valid for f in bm.faces): continue
                
                ret = bmesh.ops.bisect_plane(bm, geom=geom_to_bisect, plane_co=plane_co, plane_no=plane_no, clear_inner=False, clear_outer=False)
                bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
                if 'geom_cut' in ret:
                    for edge in ret['geom_cut']:
                        if isinstance(edge, bmesh.types.BMEdge) and edge.is_valid: edge.seam = True
            except Exception as e:
                self.report({'WARNING'}, f"Debug (_chip_one_piece): Bisect failed for {iteration_info_for_debug}: {type(e).__name__} - {e}")

        if not bm.faces or not any(f.is_valid for f in bm.faces): return False
        for f_deselect in bm.faces: 
            if f_deselect.is_valid: f_deselect.select = False

        valid_faces_for_seed = [f for f in bm.faces if f.is_valid and not f.hide]
        if not valid_faces_for_seed: return False
        
        seed_face = random.choice(valid_faces_for_seed)
        if not seed_face.is_valid: return False
        seed_face.select = True 

        try:
            bpy.ops.mesh.select_linked(delimit={'SEAM'})
        except Exception as e_sl: 
            self.report({'ERROR'}, f"Debug (_chip_one_piece): select_linked FAILED for {iteration_info_for_debug}: {type(e_sl).__name__} - {e_sl}. This should not happen if operator name is correct.")
            if not seed_face.is_valid or not seed_face.select : return False 

        selected_faces_count = sum(1 for f in bm.faces if f.is_valid and f.select)
        total_valid_faces = sum(1 for f in bm.faces if f.is_valid)
        if total_valid_faces == 0: return False
        
        return 0 < selected_faces_count < total_valid_faces


    def execute(self, context):
        source_obj = context.active_object
        scene = context.scene
        
        explosion_seed = scene.cake_explosion_seed
        random.seed(explosion_seed)

        if not scene.target_collection_name.strip():
            self.report({'ERROR'}, "Target Collection Name cannot be empty.")
            return {'CANCELLED'}
        exploded_collection_name = scene.target_collection_name

        split_mode = scene.cake_explosion_split_mode 

        target_num_pieces_total = scene.cake_explosion_num_cuts 
        if target_num_pieces_total < 1: target_num_pieces_total = 1

        original_active_name = source_obj.name
        original_object_matrix = source_obj.matrix_world.copy()
        original_source_center_world = source_obj.matrix_world.translation.copy()


        initial_state_obj = None
        if source_obj.data:
            bpy.ops.object.select_all(action='DESELECT')
            try:
                bpy.data.objects[original_active_name].select_set(True)
                context.view_layer.objects.active = bpy.data.objects[original_active_name]
            except KeyError:
                 self.report({'ERROR'}, f"Original object {original_active_name} not found for duplication.")
                 return {'CANCELLED'}

            bpy.ops.object.duplicate(linked=False)
            initial_state_obj = context.active_object
            initial_state_obj.name = f"{original_active_name}_InitialState"
            initial_state_obj.matrix_world = original_object_matrix
            while initial_state_obj.particle_systems:
                 with context.temp_override(object=initial_state_obj):
                    bpy.ops.object.particle_system_remove()
        
        bpy.ops.object.select_all(action='DESELECT')
        source_obj_ref = bpy.data.objects.get(original_active_name)
        if not source_obj_ref:
            if initial_state_obj and initial_state_obj.name in bpy.data.objects: bpy.data.objects.remove(initial_state_obj, do_unlink=True)
            self.report({'ERROR'}, f"Original object '{original_active_name}' could not be referenced.")
            return {'CANCELLED'}
            
        source_obj_ref.select_set(True)
        context.view_layer.objects.active = source_obj_ref
        
        bpy.ops.object.duplicate_move() 
        obj_to_process_for_splitting = context.active_object
        obj_to_process_for_splitting.name = f"{original_active_name}_SPLIT_BASE"
        obj_to_process_for_splitting.matrix_world = original_object_matrix
        
        user_psys = source_obj_ref.particle_systems.active
        if not user_psys: 
             self.report({'ERROR'}, f"'{original_active_name}' needs an active particle system (re-check).")
             if initial_state_obj and initial_state_obj.name in bpy.data.objects: bpy.data.objects.remove(initial_state_obj, do_unlink=True)
             if obj_to_process_for_splitting and obj_to_process_for_splitting.name in bpy.data.objects: bpy.data.objects.remove(obj_to_process_for_splitting, do_unlink=True)
             return {'CANCELLED'}

        while obj_to_process_for_splitting.particle_systems:
            with context.temp_override(object=obj_to_process_for_splitting):
                bpy.ops.object.particle_system_remove()
        
        final_pieces = []
        
        if split_mode == 'UNIFORM': 
            self.report({'INFO'}, "Using UNIFORM splitting mode (global pre-cut).")
            
            if target_num_pieces_total <= 1:
                if obj_to_process_for_splitting.data and obj_to_process_for_splitting.data.vertices:
                    final_pieces.append(obj_to_process_for_splitting)
            else:
                bpy.ops.object.select_all(action='DESELECT')
                obj_to_process_for_splitting.select_set(True)
                context.view_layer.objects.active = obj_to_process_for_splitting
                
                current_mode = obj_to_process_for_splitting.mode
                if current_mode != 'EDIT': bpy.ops.object.mode_set(mode='EDIT')
                bm = bmesh.from_edit_mesh(obj_to_process_for_splitting.data)
                
                self._apply_uniform_cuts_to_bmesh(bm, target_num_pieces_total, noise_factor=0.05) 
                
                bmesh.update_edit_mesh(obj_to_process_for_splitting.data)
                if current_mode != 'EDIT': bpy.ops.object.mode_set(mode=current_mode)
                else: bpy.ops.object.mode_set(mode='OBJECT')

                object_being_separated_iteratively = obj_to_process_for_splitting
                

                for _ in range(target_num_pieces_total + 5):
                    if not object_being_separated_iteratively or \
                       object_being_separated_iteratively.name not in bpy.data.objects or \
                       not object_being_separated_iteratively.data or \
                       not object_being_separated_iteratively.data.polygons:
                        self.report({'DEBUG'}, "Uniform: Remainder object is invalid or empty.")
                        break 

                    bpy.ops.object.select_all(action='DESELECT')
                    object_being_separated_iteratively.select_set(True)
                    context.view_layer.objects.active = object_being_separated_iteratively
                    name_of_current_remainder_obj = object_being_separated_iteratively.name

                    bpy.ops.object.mode_set(mode='EDIT')
                    bm_iter = bmesh.from_edit_mesh(object_being_separated_iteratively.data)
                    bm_iter.faces.ensure_lookup_table()

                    if not bm_iter.faces or not any(f.is_valid for f in bm_iter.faces):
                        bpy.ops.object.mode_set(mode='OBJECT')
                        self.report({'DEBUG'}, "Uniform: No valid faces in remainder BMesh.")
                        break 
                    
                    for f_sel_clear in bm_iter.faces: f_sel_clear.select = False
                    
                    seed_face_iter = next((f for f in bm_iter.faces if f.is_valid and not f.hide), None)
                    
                    if not seed_face_iter:
                        bpy.ops.object.mode_set(mode='OBJECT')
                        self.report({'DEBUG'}, "Uniform: No valid seed face found in remainder.")
                        break 
                    
                    seed_face_iter.select = True
                    

                    bmesh.update_edit_mesh(object_being_separated_iteratively.data)
                    
                    try:
                        bpy.ops.mesh.select_linked(delimit={'SEAM'})
                    except Exception as e:
                        bpy.ops.object.mode_set(mode='OBJECT')
                        self.report({'WARNING'}, f"UNIFORM separation: bpy.ops.mesh.select_linked failed: {type(e).__name__} - {e}")
                        break 

                    is_last_intended_separation = (len(final_pieces) >= target_num_pieces_total - 1)
                    
                    bpy.ops.object.mode_set(mode='OBJECT')
                    selected_poly_count = sum(1 for p in object_being_separated_iteratively.data.polygons if p.select)
                    total_poly_count = len(object_being_separated_iteratively.data.polygons)
                    bpy.ops.object.mode_set(mode='EDIT')

                    if selected_poly_count == total_poly_count and not is_last_intended_separation:

                        self.report({'INFO'}, "Uniform: Entire remainder selected, treating as last piece.")
                        bpy.ops.object.mode_set(mode='OBJECT')
                        break


                    objects_before_sep = set(o.name for o in bpy.data.objects)
                    try:
                        bpy.ops.mesh.separate(type='SELECTED')
                    except RuntimeError as e_sep:
                        bpy.ops.object.mode_set(mode='OBJECT')
                        self.report({'WARNING'}, f"UNIFORM separation: bpy.ops.mesh.separate failed: {e_sep}")
                        break
                    bpy.ops.object.mode_set(mode='OBJECT')

                    new_piece_obj = None
                    current_obj_names = set(o.name for o in bpy.data.objects)
                    diff_names = current_obj_names - objects_before_sep
                    
                    for name_cand in diff_names:
                        cand_obj = bpy.data.objects.get(name_cand)
                        if cand_obj and cand_obj.name != name_of_current_remainder_obj:
                            if cand_obj.select_get() or context.view_layer.objects.active == cand_obj :
                                new_piece_obj = cand_obj
                                break
                    if not new_piece_obj and diff_names:
                         new_piece_obj = bpy.data.objects.get(list(diff_names)[0])
                    
                    if new_piece_obj and new_piece_obj.data and new_piece_obj.data.vertices:
                        final_pieces.append(new_piece_obj)
                        remainder_obj_check = bpy.data.objects.get(name_of_current_remainder_obj)
                        if remainder_obj_check and remainder_obj_check.data and remainder_obj_check.data.polygons:
                            object_being_separated_iteratively = remainder_obj_check
                        else: 
                            object_being_separated_iteratively = None; break 
                    else:
                        self.report({'WARNING'}, "UNIFORM separation: No new piece identified or piece empty.")
                        object_being_separated_iteratively = bpy.data.objects.get(name_of_current_remainder_obj)
                        if not (object_being_separated_iteratively and object_being_separated_iteratively.data and object_being_separated_iteratively.data.polygons):
                            break 
                
                if object_being_separated_iteratively and \
                   object_being_separated_iteratively.name in bpy.data.objects and \
                   object_being_separated_iteratively.data and \
                   object_being_separated_iteratively.data.vertices:
                    if not any(p is object_being_separated_iteratively for p in final_pieces):
                        final_pieces.append(object_being_separated_iteratively)
                elif object_being_separated_iteratively and object_being_separated_iteratively.name in bpy.data.objects:
                    bpy.data.objects.remove(object_being_separated_iteratively, do_unlink=True)
                    
        elif split_mode in ['NON_UNIFORM', 'RANDOM_CHIPPING']:
            self.report({'INFO'}, f"Using iterative chipping mode: {split_mode}.")
            obj_to_carve_from = obj_to_process_for_splitting

            num_bisections_per_chip = 1
            if split_mode == 'NON_UNIFORM':
                num_bisections_per_chip = random.randint(1, 2)
            elif split_mode == 'RANDOM_CHIPPING':
                num_bisections_per_chip = random.randint(2, 5) 

            for iteration_count in range(target_num_pieces_total - 1):
                if not obj_to_carve_from or \
                   obj_to_carve_from.name not in bpy.data.objects or \
                   not obj_to_carve_from.data or \
                   not obj_to_carve_from.data.vertices or \
                   not obj_to_carve_from.data.polygons:
                    self.report({'DEBUG'}, f"Chipping: obj_to_carve_from invalid for iter {iteration_count}")
                    break

                bpy.ops.object.select_all(action='DESELECT')
                obj_to_carve_from.select_set(True)
                context.view_layer.objects.active = obj_to_carve_from
                name_of_object_being_reduced = obj_to_carve_from.name
                
                current_mode = obj_to_carve_from.mode
                if current_mode != 'EDIT': bpy.ops.object.mode_set(mode='EDIT')
                
                bm = bmesh.from_edit_mesh(obj_to_carve_from.data)
                debug_info = f"Chunk: {name_of_object_being_reduced}, Iter: {iteration_count}, Mode: {split_mode}"
                
                selection_successful = self._chip_one_piece(bm, context, num_bisections_per_chip, debug_info)
                
                if not selection_successful:
                    if current_mode != 'EDIT': bpy.ops.object.mode_set(mode=current_mode)
                    else: bpy.ops.object.mode_set(mode='OBJECT')
                    self.report({'INFO'}, f"Chipping: _chip_one_piece selection not successful for {name_of_object_being_reduced}")
                    continue 

                objects_before_sep = set(o.name for o in bpy.data.objects)
                try:
                    bpy.ops.mesh.separate(type='SELECTED')
                except RuntimeError as e_sep:
                     self.report({'WARNING'}, f"Chipping: separate op failed for {name_of_object_being_reduced}: {e_sep}")
                     if current_mode != 'EDIT': bpy.ops.object.mode_set(mode=current_mode)
                     else: bpy.ops.object.mode_set(mode='OBJECT')
                     continue
                
                if current_mode != 'EDIT': bpy.ops.object.mode_set(mode=current_mode)
                else: bpy.ops.object.mode_set(mode='OBJECT')
                
                new_piece = None
                new_obj_names = set(o.name for o in bpy.data.objects) - objects_before_sep
                temp_remainder = bpy.data.objects.get(name_of_object_being_reduced)

                for n_name in new_obj_names:
                    obj_cand = bpy.data.objects.get(n_name)
                    if obj_cand and obj_cand != temp_remainder :
                        new_piece = obj_cand; break
                if not new_piece:
                    for sel_obj in context.selected_objects:
                        if sel_obj.name in new_obj_names and sel_obj != temp_remainder:
                            new_piece = sel_obj; break
                
                if new_piece and new_piece.data and new_piece.data.vertices:
                    final_pieces.append(new_piece)
                    if temp_remainder and temp_remainder.data and temp_remainder.data.vertices:
                        obj_to_carve_from = temp_remainder
                    else: 
                        if temp_remainder and temp_remainder.name in bpy.data.objects: bpy.data.objects.remove(temp_remainder, do_unlink=True)
                        obj_to_carve_from = None; break 
                else: 
                    if new_piece and new_piece.name in bpy.data.objects: bpy.data.objects.remove(new_piece, do_unlink=True)
                    if not (temp_remainder and temp_remainder.data and temp_remainder.data.vertices):
                        if temp_remainder and temp_remainder.name in bpy.data.objects: bpy.data.objects.remove(temp_remainder, do_unlink=True)
                        obj_to_carve_from = None; break
            
            if obj_to_carve_from and obj_to_carve_from.name in bpy.data.objects and \
               obj_to_carve_from.data and obj_to_carve_from.data.vertices:
                if not any(p is obj_to_carve_from for p in final_pieces):
                    final_pieces.append(obj_to_carve_from)
            elif obj_to_carve_from and obj_to_carve_from.name in bpy.data.objects:
                bpy.data.objects.remove(obj_to_carve_from, do_unlink=True)
        
        else:
            self.report({'ERROR'}, f"Unknown split_mode defined: {split_mode}")
            if initial_state_obj and initial_state_obj.name in bpy.data.objects: bpy.data.objects.remove(initial_state_obj, do_unlink=True)
            if obj_to_process_for_splitting and obj_to_process_for_splitting.name in bpy.data.objects: bpy.data.objects.remove(obj_to_process_for_splitting, do_unlink=True)
            return {'CANCELLED'}

        # --- Post-splitting ---
        valid_pieces_cleaned = []
        seen_final_objects = set()
        for p_obj in final_pieces:
            if p_obj and p_obj.name in bpy.data.objects and p_obj.data and p_obj.data.vertices:
                if p_obj not in seen_final_objects:
                    valid_pieces_cleaned.append(p_obj)
                    seen_final_objects.add(p_obj)
        final_pieces = valid_pieces_cleaned

        if not final_pieces:
            self.report({'ERROR'}, "Splitting resulted in no valid pieces.")
            if initial_state_obj and initial_state_obj.name in bpy.data.objects: bpy.data.objects.remove(initial_state_obj, do_unlink=True)
            return {'CANCELLED'}
        
        exploded_collection = create_or_clear_collection(exploded_collection_name)

        if initial_state_obj and initial_state_obj.name in bpy.data.objects:
            for coll in initial_state_obj.users_collection: coll.objects.unlink(initial_state_obj)
            exploded_collection.objects.link(initial_state_obj)
            bpy.ops.object.select_all(action='DESELECT')
            initial_state_obj.select_set(True)
            context.view_layer.objects.active = initial_state_obj
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        else: initial_state_obj = None 

        actual_created_piece_count = len(final_pieces)
        for i, piece in enumerate(final_pieces):
            if piece.name not in bpy.data.objects : continue 
            piece.name = f"{original_active_name}_piece_{i:03d}"
            for coll_to_unlink_from in piece.users_collection: coll_to_unlink_from.objects.unlink(piece)
            if piece.name not in exploded_collection.objects: exploded_collection.objects.link(piece)
            bpy.ops.object.select_all(action='DESELECT')
            piece.select_set(True)
            context.view_layer.objects.active = piece
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        
        num_particles_in_user_system = user_psys.settings.count
        
        # --- Directional Piece Assignment ---
        pieces_for_animation = []
        if final_pieces and user_psys:

            particle_eval_frame = scene.frame_start 
            if hasattr(user_psys.settings, 'frame_start'):
                 particle_eval_frame = max(scene.frame_start, int(user_psys.settings.frame_start))
            
            self.report({'INFO'}, "Attempting directional particle assignment...")
            pieces_for_animation = get_directionally_matched_pieces(
                original_source_center_world, 
                list(final_pieces),
                user_psys, 
                particle_eval_frame,
                context
            )
            self.report({'INFO'}, f"Directional matching resulted in {len(pieces_for_animation)} pieces for animation.")
        
        if not pieces_for_animation and final_pieces:
             self.report({'WARNING'}, "Directional matching failed or yielded no pieces; using sequential assignment.")
             pieces_for_animation = final_pieces[:min(len(final_pieces), num_particles_in_user_system)]
        elif not final_pieces:
             pieces_for_animation = []


        num_pieces_to_animate_final = len(pieces_for_animation)


        bake_anim_start_frame = scene.frame_start
        bake_anim_end_frame = scene.frame_end 
        bake_anim_step = scene.bake_step

        if initial_state_obj and initial_state_obj.name in bpy.data.objects:
            initial_state_obj.location = original_object_matrix.translation
            initial_state_obj.rotation_mode = source_obj_ref.rotation_mode 
            if source_obj_ref.rotation_mode == 'QUATERNION':
                initial_state_obj.rotation_quaternion = original_object_matrix.to_quaternion()
            elif source_obj_ref.rotation_mode == 'AXIS_ANGLE':
                initial_state_obj.rotation_axis_angle = original_object_matrix.to_axis_angle()
            else: 
                initial_state_obj.rotation_euler = original_object_matrix.to_euler(source_obj_ref.rotation_euler.order)
            initial_state_obj.scale = original_object_matrix.to_scale()
            keyframe_object(initial_state_obj, bake_anim_start_frame)
            initial_state_obj.scale = (0.001, 0.001, 0.001)
            initial_state_obj.keyframe_insert(data_path="scale", frame=bake_anim_start_frame + 1)

        for piece in pieces_for_animation:
            if piece and piece.name in bpy.data.objects:
                piece.scale = (0.001, 0.001, 0.001)
                piece.keyframe_insert(data_path="scale", frame=bake_anim_start_frame)

        if pieces_for_animation:
            self.report({'INFO'}, (f"Animating {num_pieces_to_animate_final} pieces. Initial state on frame {bake_anim_start_frame}, fragments from {bake_anim_start_frame + 1}."))
            match_keyframe_objects(user_psys, pieces_for_animation, 
                                   bake_anim_start_frame, bake_anim_end_frame,
                                   bake_anim_step, keyframe_offset=1) 
            if actual_created_piece_count > num_pieces_to_animate_final :
                 self.report({'WARNING'}, (f"{actual_created_piece_count - num_pieces_to_animate_final} pieces created but not animated (either no matching particle or particle limit)."))
        elif actual_created_piece_count > 0:
             self.report({'WARNING'}, f"{actual_created_piece_count} pieces created, but none animated.")
        else:
            self.report({'WARNING'}, "No pieces to animate.")

        self.report({'INFO'}, (f"Explosion for '{original_active_name}': {actual_created_piece_count} pieces created in collection '{exploded_collection.name}'. {num_pieces_to_animate_final} animated."))
        
        bpy.ops.object.select_all(action='DESELECT')
        active_obj_set = False
        all_involved_objects = []
        if initial_state_obj and initial_state_obj.name in bpy.data.objects: all_involved_objects.append(initial_state_obj)
        all_involved_objects.extend(p for p in final_pieces if p and p.name in bpy.data.objects)

        for obj_to_select in all_involved_objects:
            if obj_to_select.name in bpy.data.objects:
                bpy.data.objects[obj_to_select.name].select_set(True)
                if not active_obj_set:
                    context.view_layer.objects.active = bpy.data.objects[obj_to_select.name]
                    active_obj_set = True
        
        if not active_obj_set and original_active_name in bpy.data.objects :
            bpy.data.objects[original_active_name].select_set(True)
            context.view_layer.objects.active = bpy.data.objects[original_active_name]
            
        return {'FINISHED'}


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

class CAKE_OT_AdjustExplosionParticles(bpy.types.Operator):
    """Adjust active particle system for CakeExplosion prerequisites"""
    bl_idname = "cake.adjust_explosion_particles"
    bl_label = "Sets the Particle System settings to create a basic Explosion simulation, feel free to tweak them furthermore"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.particle_systems.active

    def execute(self, context):
        obj = context.active_object
        scene = context.scene

        if not obj or not obj.particle_systems.active:
            self.report({'WARNING'}, "No active object with an active particle system.")
            return {'CANCELLED'}

        psys = obj.particle_systems.active
        settings = psys.settings

        try:
            # 1. Emission Number
            settings.count = scene.cake_explosion_num_cuts + 1
            
            # 2. Frame Start and Frame End
            settings.frame_start = 1.0
            settings.frame_end = 1.0
            
            # 3. Velocity Normal
            settings.normal_factor = 10.0
            
            # 4. Rotation Active
            settings.use_rotations = True
            
            # 5. Angular Velocity (assuming 'NONE' or 'VELOCITY' mode, setting factor)
            # For more specific control, angular_velocity_mode might be needed.
            # Blender's default is often 'NONE' or 'VELOCITY' for factor.
            # If you need a specific mode (like 'RAND'), let me know.
            settings.angular_velocity_factor = 2.0 
            # You might also want to ensure dynamic rotation is on if using physics based rotation
            # settings.use_dynamic_rotation = True 

            # 6. Render Scale (particle_size for instanced objects/collections)
            settings.particle_size = 1.0
            # If you are using 'Render As: Object' or 'Render As: Collection', 
            # this controls the instance scale.

            self.report({'INFO'}, f"Particle system '{psys.name}' adjusted for explosion.")

        except AttributeError as e:
            self.report({'ERROR'}, f"Failed to set a particle property: {e}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"An unexpected error occurred: {e}")
            return {'CANCELLED'}

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
    bpy.types.Scene.cake_explosion_num_cuts = bpy.props.IntProperty(
        name="Number of Cuts",
        description="Number of random cuts to perform on the mesh. More cuts generally result in more pieces",
        default=10,
        min=1,
        soft_max=50
    )
    bpy.types.Scene.cake_explosion_split_mode = bpy.props.EnumProperty(
        name="Splitting Mode",
        items=[
            ('NON_UNIFORM', "Non-Uniform (Chip)", "Chips pieces iteratively; sizes can vary (original method)."),
            ('RANDOM_CHIPPING', "Random Chipping (Aggressive)", "Iterative chipping with more random cuts per step."),
        ],
        default='NON_UNIFORM',
        description="Method used to split the mesh during explosion."
    )
    bpy.types.Scene.show_cake_explosion_options = bpy.props.BoolProperty(
        name="Show Cake Explosion",
        description="Show options for the Cake Explosion feature",
        default=False
    )
    bpy.types.Scene.cake_explosion_seed = bpy.props.IntProperty(
        name="Explosion Seed",
        description="Seed for random cuts. Change to get different fracture patterns.",
        default=0 
    )
    bpy.utils.register_class(CAKE_OT_CakeExplosion)
    bpy.utils.register_class(CAKE_OT_AdjustExplosionParticles)
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
    bpy.utils.unregister_class(CAKE_OT_CakeExplosion)
    bpy.utils.unregister_class(CAKE_OT_AdjustExplosionParticles)
    del bpy.types.Scene.cake_explosion_num_cuts
    del bpy.types.Scene.cake_explosion_split_mode
    del bpy.types.Scene.cake_explosion_seed
    del bpy.types.Scene.show_cake_explosion_options
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
