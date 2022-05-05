bl_info = {
    "name" : "CakeParticles",
    "author" : "A group of People that loves Cakes", 
    "description" : "An addon that Makes Baking Particles into Objects easy as Eating a Piece of Cake",
    "blender" : (3, 0, 0),
    "version" : (1, 0, 3),
    "location" : "ObjectProperties",
    "waring" : "",
    "doc_url": "https://sites.google.com/view/cakeparticlesdocs/home-page", 
    "tracker_url": "", 
    "category" : "Physics" 
}


import bpy
import bpy.utils.previews



def string_to_int(value):
    if value.isdigit():
        return int(value)
    return 0

def string_to_icon(value):
    if value in bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys():
        return bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items[value].value
    return string_to_int(value)
    
def icon_to_string(value):
    for icon in bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items:
        if icon.value == value:
            return icon.name
    return "NONE"
    
def enum_set_to_string(value):
    if type(value) == set:
        if len(value) > 0:
            return "[" + (", ").join(list(value)) + "]"
        return "[]"
    return value
    
def string_to_type(value, to_type, default):
    try:
        value = to_type(value)
    except:
        value = default
    return value

addon_keymaps = {}
_icons = None
addonmain = {}



import bpy


KEYFRAME_LOCATION = True
KEYFRAME_ROTATION = True
KEYFRAME_SCALE = True
KEYFRAME_VISIBILITY = False
KEYFRAME_VISIBILITY_SCALE = True


def create_objects_for_particles(ps, obj):

    obj_list = []
    mesh = obj.data
    particles_coll = bpy.data.collections.new(name="particles")
    bpy.context.scene.collection.children.link(particles_coll)

    for i, _ in enumerate(ps.particles):
        dupli = bpy.data.objects.new(
                    name="particle.{:03d}".format(i),
                    object_data=mesh)
        particles_coll.objects.link(dupli)
        obj_list.append(dupli)
    return obj_list

def match_and_keyframe_objects(ps, obj_list, start_frame, end_frame):

    for frame in range(start_frame, end_frame + 1):
        print("frame {} processed".format(frame))
        bpy.context.scene.frame_set(frame)
        for p, obj in zip(ps.particles, obj_list):
            match_object_to_particle(p, obj)
            keyframe_obj(obj)

def match_object_to_particle(p, obj):

    loc = p.location
    rot = p.rotation
    size = p.size
    if p.alive_state == 'ALIVE':
        vis = True
    else:
        vis = False
    obj.location = loc
 
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rot
    if KEYFRAME_VISIBILITY_SCALE:
        if vis:
            obj.scale = (size, size, size)
        if not vis:
            obj.scale = (0.001, 0.001, 0.001)
    obj.hide_viewport = (vis)
    obj.hide_render = (vis)

def keyframe_obj(obj):

    if KEYFRAME_LOCATION:
        obj.keyframe_insert("location")
    if KEYFRAME_ROTATION:
        obj.keyframe_insert("rotation_quaternion")
    if KEYFRAME_SCALE:
        obj.keyframe_insert("scale")
    if KEYFRAME_VISIBILITY:
        obj.keyframe_insert("hide_viewport")
        obj.keyframe_insert("hide_render")


def main():

    depsgraph = bpy.context.evaluated_depsgraph_get()

    ps_obj = bpy.context.object
    ps_obj_evaluated = depsgraph.objects[ ps_obj.name ]
    obj = [obj for obj in bpy.context.selected_objects if obj != ps_obj][0]

    for psy in ps_obj_evaluated.particle_systems:         
        ps = psy
        start_frame = bpy.context.scene.frame_start
        end_frame = bpy.context.scene.frame_end
        obj_list = create_objects_for_particles(ps, obj)
        match_and_keyframe_objects(ps, obj_list, start_frame, end_frame)
        
class SNA_PT_CAKEPARTICLES_A5926(bpy.types.Panel):
    bl_label = 'CakeParticles'
    bl_idname = 'SNA_PT_CAKEPARTICLES_A5926'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_category = 'CakeParticles'
    bl_order = 0
    bl_options = {'HEADER_LAYOUT_EXPAND'}
    
    bl_ui_units_x=0
    @classmethod
    def poll(cls, context):
        return not (False)
    
    def draw_header(self, context):
        layout = self.layout
        
    def draw(self, context):
        layout = self.layout
        box_CDFD2 = layout.box()
        box_CDFD2.alert = False
        box_CDFD2.enabled = True
        box_CDFD2.use_property_split = False
        box_CDFD2.use_property_decorate = True
        box_CDFD2.alignment = 'Left'.upper()
        box_CDFD2.scale_x = 0.5
        box_CDFD2.scale_y = 1.5
        box_CDFD2.label(text='Kindly Follow the Instructions', icon_value=112)
        col_5B084 = box_CDFD2.column(heading='', align=True)
        col_5B084.alert = False
        col_5B084.enabled = True
        col_5B084.use_property_split = False
        col_5B084.use_property_decorate = False
        col_5B084.scale_x = 1.0
        col_5B084.scale_y = 1.0
        col_5B084.alignment = 'Left'.upper()
        col_5B084.label(text='Keep the Emitter Active ', icon_value=256)
        col_5B084.label(text='and the Particle Object selected', icon_value=0)
        op = box_CDFD2.operator('sna.opbakeparticles_81b66', text='BakeParticles into KeyFrames', icon_value=181, emboss=True, depress=False)
        box_801E9 = layout.box()
        box_801E9.alert = False
        box_801E9.enabled = True
        box_801E9.use_property_split = False
        box_801E9.use_property_decorate = True
        box_801E9.alignment = 'Left'.upper()
        box_801E9.scale_x = 0.5
        box_801E9.scale_y = 2.0
        box_801E9.label(text='-Select all the Objects in the new "particles" Collection ', icon_value=256)
        op = box_801E9.operator('wm.alembic_export', text='Export Alembic', icon_value=70, emboss=True, depress=False)
        op.check_existing = True
        op.filter_alembic = True
        op.filter_folder = True
        op.display_type = 'THUMBNAIL'
        op.start = 0
        op.end = 0
        op.selected = True
        op.use_instancing = False
        op.global_scale = 1.0
        op.triangulate = False
        op.export_hair = False
        op.export_particles = False
        op.export_custom_properties = False
        op.as_background_job = False
        op.evaluation_mode = 'RENDER'
        box_A68B6 = layout.box()
        box_A68B6.alert = False
        box_A68B6.enabled = True
        box_A68B6.use_property_split = False
        box_A68B6.use_property_decorate = True
        box_A68B6.alignment = 'Left'.upper()
        box_A68B6.scale_x = 0.20000000298023224
        box_A68B6.scale_y = 3.0
        box_A68B6.label(text='+Create a New Collection to Import the Particles ', icon_value=22)
        box_A68B6.label(text='Keep it Active and Empty', icon_value=439)
        op = box_A68B6.operator('wm.alembic_import', text='Import the Alembic', icon_value=420, emboss=True, depress=False)
        op.filter_alembic = True
        op.display_type = 'DEFAULT'
        op.scale = 1.0
        op.set_frame_range = False
        op.validate_meshes = False
        op.always_add_cache_reader = False
        op.is_sequence = False
        box_E83B6 = layout.box()
        box_E83B6.alert = False
        box_E83B6.enabled = True
        box_E83B6.use_property_split = False
        box_E83B6.use_property_decorate = True
        box_E83B6.alignment = 'Left'.upper()
        box_E83B6.scale_x = 0.5
        box_E83B6.scale_y = 2.0
        box_E83B6.label(text="Now you're free to Bake your Animation onto an .Fbx file.", icon_value=221)
        op = box_E83B6.operator('export_scene.fbx', text='Fbx Export', icon_value=88, emboss=True, depress=False)
        op.check_existing = True
        op.use_selection = True
        op.use_active_collection = False
        op.global_scale = 1.0
        op.use_mesh_edges = False
        op.use_custom_props = True
        op.add_leaf_bones = False
        op.use_armature_deform_only = False
        op.bake_anim = True
        op.bake_anim_use_all_bones = False
        op.bake_anim_use_nla_strips = False
        op.bake_anim_use_all_actions = False
        op.bake_anim_force_startend_keying = True
        op.bake_anim_step = 1.0
        op.bake_anim_simplify_factor = 1.0
        op.axis_forward = '-Z'
        op.axis_up = 'Y'
class SNA_OT_Opbakeparticles_81B66(bpy.types.Operator):
    bl_idname = "sna.opbakeparticles_81b66"
    bl_label = "OPBakeParticles"
    bl_description = "BakeParticles"
    bl_options = {"REGISTER", "UNDO"}
    
    
    @classmethod
    def poll(cls, context):
        return not False
    def execute(self, context):
        exec('main()')
        return {"FINISHED"}
    
    def invoke(self, context, event):
        
        
        return self.execute(context)



def register():
    
    global _icons
    _icons = bpy.utils.previews.new()
    
    
    bpy.utils.register_class(SNA_PT_CAKEPARTICLES_A5926)
    bpy.utils.register_class(SNA_OT_Opbakeparticles_81B66)

def unregister():
    
    global _icons
    bpy.utils.previews.remove(_icons)
    
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    for km, kmi in addon_keymaps.values():
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    
    bpy.utils.unregister_class(SNA_PT_CAKEPARTICLES_A5926)
    bpy.utils.unregister_class(SNA_OT_Opbakeparticles_81B66)

