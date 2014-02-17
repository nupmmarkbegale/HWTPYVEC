# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

bl_info = {
    "name": "Inset Polygon",
    "author": "Howard Trickey",
    "version": (1, 0),
    "blender": (2, 69, 9),
    "location": "View3D > Tools",
    "description": "Make an inset polygon inside selection.",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"
        "Scripts/Modeling/Inset-Polygon",
    "tracker_url": "https://developer.blender.org/T27290",
    "category": "Mesh"}


if "bpy" in locals():
    import imp
else:
    from . import geom
    from . import model
    from . import offset
    from . import triquad

import math
import bpy
import bmesh
import mathutils
from bpy.props import (BoolProperty,
                       EnumProperty,
                       FloatProperty,
                       )


class Inset(bpy.types.Operator):
    bl_idname = "mesh.insetpoly"
    bl_label = "Inset Polygon"
    bl_description = "Make an inset polygon inside selection"
    bl_options = {'REGISTER', 'UNDO'}

    inset_amount = FloatProperty(name="Amount",
        description="Amount to move inset edges",
        default=5.0,
        min=0.0,
        max=1000.0,
        soft_min=0.0,
        soft_max=100.0,
        unit='LENGTH')
    inset_height = FloatProperty(name="Height",
        description="Amount to raise inset faces",
        default=0.0,
        min=-10000.0,
        max=10000.0,
        soft_min=-500.0,
        soft_max=500.0,
        unit='LENGTH')
    region = BoolProperty(name="Region",
        description="Inset selection as one region?",
        default=True)
    scale = EnumProperty(name="Scale",
        description="Scale for amount",
        items=[
            ('PERCENT', "Percent",
                "Percentage of maximum inset amount"),
            ('ABSOLUTE', "Absolute",
                "Length in blender units")
            ],
        default='PERCENT')

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH')

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label("Inset Options:")
        box.prop(self, "scale")
        box.prop(self, "inset_amount")
        box.prop(self, "inset_height")
        box.prop(self, "region")

    def invoke(self, context, event):
        self.action(context)
        return {'FINISHED'}

    def execute(self, context):
        self.action(context)
        return {'FINISHED'}

    def action(self, context):
        save_global_undo = bpy.context.user_preferences.edit.use_global_undo
        bpy.context.user_preferences.edit.use_global_undo = False
        obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        do_inset(bm, self.inset_amount, self.inset_height, self.region,
            self.scale == 'PERCENT')
        bpy.context.user_preferences.edit.use_global_undo = save_global_undo


def do_inset(bm, amount, height, region, as_percent):
    if amount <= 0.0:
        return
    pitch = math.atan(height / amount)
    selfaces = []
    selface_indices = []
    for face in bm.faces:
        if face.select and not face.hide:
            selfaces.append(face)
            selface_indices.append(face.index)
    m = geom.Model()
    # if add all bm.verts, coord indices will line up
    # Note: not using Points.AddPoint which does dup elim
    # because then would have to map vertices in and out
    m.points.pos = [v.co.to_tuple() for v in bm.verts]
    for f in selfaces:
        m.faces.append([v.index for v in f.verts])
        m.face_data.append(f.index)
    orig_numv = len(m.points.pos)
    orig_numf = len(m.faces)
    model.BevelSelectionInModel(m, amount, pitch, True, region, as_percent)
    if len(m.faces) == orig_numf:
        # something went wrong with Bevel - just treat as no-op
        return
    # make new BMVerts; indices will line up properly if add in order
    for i in range(orig_numv, len(m.points.pos)):
        bm.verts.new(m.points.pos[i])
    # make new BMFaces
    for i in range(orig_numf, len(m.faces)):
        f = m.faces[i]
        face_verts = [bm.verts[k] for k in f]
        # copy face attributes from old face that it was derived from
        bfi = m.face_data[i]
        if bfi and 0 <= bfi < orig_numf:
            newf = bm.faces.new(face_verts, bm.faces[bfi])
        else:
            newf = bm.faces.new(face_verts)
    # remove original faces
    save_select_mode = bpy.context.tool_settings.mesh_select_mode
    bpy.context.tool_settings.mesh_select_mode = [False, False, True]
    bpy.ops.mesh.select_all(action='DESELECT')
    for fi in selface_indices:
        bm.faces[fi].select = True
    bpy.ops.mesh.delete(type='FACE')
    bpy.context.tool_settings.mesh_select_mode = save_select_mode


def panel_func(self, context):
    self.layout.label(text="Inset Polygon:")
    self.layout.operator("mesh.insetpoly", text="Inset")


def register():
    bpy.utils.register_class(Inset)
    bpy.types.VIEW3D_PT_tools_meshedit.append(panel_func)


def unregister():
    bpy.utils.unregister_class(Inset)
    bpy.types.VIEW3D_PT_tools_meshedit.remove(panel_func)


if __name__ == "__main__":
    register()
