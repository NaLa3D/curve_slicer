bl_info = {
    "name": "Curve View Trimmer (ビュー投影トリマー)",
    "author": "Antigravity Pair",
    "version": (2, 2, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Curve Slicer",
    "description": "アノテーション（手描き線）からビュー方向に沿って立体をトリム（削り落とし）するツール",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector, Quaternion


def get_3d_view_rotation(context):
    """現在の3Dビューの視線回転（view_rotation）を取得"""
    if context.region_data and hasattr(context.region_data, "view_rotation"):
        return context.region_data.view_rotation
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    return space.region_3d.view_rotation
    return Quaternion((1, 0, 0, 0))


def get_active_annotation_strokes(context):
    """Blender各バージョンに対応したアノテーションストロークの取得"""
    gp_list = []
    if hasattr(context, "annotation_data") and context.annotation_data:
        gp_list.append(context.annotation_data)
    if hasattr(context.scene, "annotation") and context.scene.annotation:
        gp_list.append(context.scene.annotation)
    if hasattr(context.scene, "grease_pencil") and context.scene.grease_pencil:
        gp_list.append(context.scene.grease_pencil)
    if hasattr(bpy.data, "annotations"):
        for a in bpy.data.annotations:
            if a not in gp_list:
                gp_list.append(a)

    strokes = []
    for gp in gp_list:
        for layer in gp.layers:
            if hasattr(layer, "active_frame") and layer.active_frame and layer.active_frame.strokes:
                for stroke in layer.active_frame.strokes:
                    strokes.append((gp, layer, stroke))
            elif hasattr(layer, "frames"):
                for frame in layer.frames:
                    for stroke in frame.strokes:
                        strokes.append((gp, layer, stroke))

    return strokes


def get_target_mesh(context):
    """シーン内の対象メッシュを取得"""
    if context.active_object and context.active_object.type == 'MESH' and not context.active_object.name.startswith("Slicer_Cutter"):
        return context.active_object
    for obj in context.selected_objects:
        if obj.type == 'MESH' and not obj.name.startswith("Slicer_Cutter"):
            return obj
    for obj in context.scene.objects:
        if obj.type == 'MESH' and not obj.name.startswith("Slicer_Cutter"):
            return obj
    return None


def get_cutter_object(context):
    """シーン内のカッターオブジェクトを取得"""
    if context.active_object and context.active_object.name.startswith("Slicer_Cutter"):
        return context.active_object
    for obj in context.selected_objects:
        if obj.name.startswith("Slicer_Cutter"):
            return obj
    for obj in context.scene.objects:
        if obj.name.startswith("Slicer_Cutter"):
            return obj
    return None


def calculate_screen_normals(points, view_fwd):
    """キワの点列に対して画面上で垂直な法線ベクトルを計算"""
    normals = []
    n_pts = len(points)
    for i in range(n_pts):
        if i < n_pts - 1:
            t = (points[i + 1] - points[i]).normalized()
        else:
            t = (points[i] - points[i - 1]).normalized()
        
        n = view_fwd.cross(t).normalized()
        if n.length < 0.001:
            n = Vector((0, 1, 0))
        normals.append(n)
    return normals


def rebuild_cutter_ribbon(cutter_obj, width, flip_dir):
    """画面上のプレビュー用リボンメッシュを再構築"""
    if not cutter_obj or "base_points" not in cutter_obj:
        return

    base_points = [Vector(p) for p in cutter_obj["base_points"]]
    normals = [Vector(n) for n in cutter_obj["normals"]]

    mesh = cutter_obj.data
    bm = bmesh.new()

    base_verts = []
    offset_verts = []

    for i, pt in enumerate(base_points):
        n = normals[i] * (width * flip_dir)
        bv = bm.verts.new(pt)
        ov = bm.verts.new(pt + n)
        base_verts.append(bv)
        offset_verts.append(ov)

    bm.verts.ensure_lookup_table()

    for i in range(len(base_points) - 1):
        v1 = base_verts[i]
        v2 = base_verts[i + 1]
        v3 = offset_verts[i + 1]
        v4 = offset_verts[i]
        bm.faces.new([v1, v2, v3, v4])

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def on_ribbon_width_update(self, context):
    """スライダー操作時にリボンメッシュをリアルタイム更新"""
    cutter_obj = get_cutter_object(context)
    if cutter_obj and "base_points" in cutter_obj:
        flip_dir = cutter_obj.get("flip_dir", 1.0)
        rebuild_cutter_ribbon(cutter_obj, self.ribbon_height, flip_dir)


class CURVESLICER_OT_convert_annotation(bpy.types.Operator):
    """描いた線を「キワ」にして、ビュー方向を基準としたリボンを生成します"""
    bl_idname = "curve_slicer.convert_annotation"
    bl_label = "① ペンの線をリボン化"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target = get_target_mesh(context)
        stroke_tuples = get_active_annotation_strokes(context)

        if not stroke_tuples:
            self.report({'WARNING'}, "ペンの線が見つかりません。Dキー+ドラッグで線を描いてください。")
            return {'CANCELLED'}

        gp, layer, stroke = stroke_tuples[-1]
        raw_points = [Vector(pt.co) for pt in stroke.points]

        if len(raw_points) < 2:
            self.report({'WARNING'}, "線が短すぎます。もう少し長めに描いてください。")
            return {'CANCELLED'}

        target_count = 20
        step = max(1, len(raw_points) // target_count)
        sampled_points = raw_points[::step]
        if raw_points[-1] not in sampled_points:
            sampled_points.append(raw_points[-1])

        # 両端の自動延長
        p_start = sampled_points[0]
        p_next = sampled_points[1]
        dir_start = (p_start - p_next).normalized()
        sampled_points[0] = p_start + dir_start * 1.0

        p_end = sampled_points[-1]
        p_prev = sampled_points[-2]
        dir_end = (p_end - p_prev).normalized()
        sampled_points[-1] = p_end + dir_end * 1.0

        view_rot = get_3d_view_rotation(context)
        view_fwd = (view_rot @ Vector((0, 0, -1))).normalized()

        normals = calculate_screen_normals(sampled_points, view_fwd)

        if target:
            bbox_corners = [target.matrix_world @ Vector(corner) for corner in target.bound_box]
            size_x = max(c.x for c in bbox_corners) - min(c.x for c in bbox_corners)
            size_y = max(c.y for c in bbox_corners) - min(c.y for c in bbox_corners)
            size_z = max(c.z for c in bbox_corners) - min(c.z for c in bbox_corners)
            max_dim = max(size_x, size_y, size_z, 1.0)
            initial_width = max_dim * 0.8
        else:
            initial_width = 2.0

        context.scene.ribbon_height = initial_width

        old_cutter = bpy.data.objects.get("Slicer_Cutter")
        if old_cutter:
            bpy.data.objects.remove(old_cutter, do_unlink=True)

        mesh = bpy.data.meshes.new("Slicer_Cutter_Mesh")
        cutter_obj = bpy.data.objects.new("Slicer_Cutter", mesh)
        
        cutter_obj["flip_dir"] = 1.0
        cutter_obj["view_fwd"] = list(view_fwd)
        cutter_obj["base_points"] = [list(p) for p in sampled_points]
        cutter_obj["normals"] = [list(n) for n in normals]

        context.collection.objects.link(cutter_obj)
        rebuild_cutter_ribbon(cutter_obj, initial_width, 1.0)

        # アノテーションのストロークを消去
        try:
            if hasattr(layer, "active_frame") and layer.active_frame and stroke in layer.active_frame.strokes:
                layer.active_frame.strokes.remove(stroke)
            else:
                for f in layer.frames:
                    if stroke in f.strokes:
                        f.strokes.remove(stroke)
        except Exception:
            pass

        bpy.ops.object.select_all(action='DESELECT')
        cutter_obj.select_set(True)
        context.view_layer.objects.active = cutter_obj

        self.report({'INFO'}, "リボンを作成しました！『スライス（トリム）』で消去できます。")
        return {'FINISHED'}


class CURVESLICER_OT_flip_direction(bpy.types.Operator):
    """リボンの伸びる向きを反対側に反転（Flip）します"""
    bl_idname = "curve_slicer.flip_direction"
    bl_label = "🔄 消す向きを反転 (Flip)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        cutter_obj = get_cutter_object(context)

        if not cutter_obj or "base_points" not in cutter_obj:
            self.report({'WARNING'}, "反転可能なカッターリボンが見つかりません。")
            return {'CANCELLED'}

        current_dir = cutter_obj.get("flip_dir", 1.0)
        new_dir = -1.0 * current_dir
        cutter_obj["flip_dir"] = new_dir

        rebuild_cutter_ribbon(cutter_obj, context.scene.ribbon_height, new_dir)

        self.report({'INFO'}, "消去する向きを反転しました！")
        return {'FINISHED'}


class CURVESLICER_OT_clear_annotation(bpy.types.Operator):
    """画面上のアノテーション（ペン線）や作成途中のリボンを一発消去・リセットします"""
    bl_idname = "curve_slicer.clear_annotation"
    bl_label = "🗑️ ペン線を消す / リセット"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 1. アノテーションデータの全削除
        if hasattr(bpy.data, "annotations"):
            for gp in list(bpy.data.annotations):
                bpy.data.annotations.remove(gp)
        if hasattr(context.scene, "annotation") and context.scene.annotation:
            context.scene.annotation = None
        if hasattr(bpy.data, "grease_pencils"):
            for gp in list(bpy.data.grease_pencils):
                if gp.name.startswith("Annotation"):
                    bpy.data.grease_pencils.remove(gp)

        # 2. プレビュー用カッターリボンの削除
        old_cutter = bpy.data.objects.get("Slicer_Cutter")
        if old_cutter:
            bpy.data.objects.remove(old_cutter, do_unlink=True)

        self.report({'INFO'}, "アノテーションとリボンをクリアしました。")
        return {'FINISHED'}


class CURVESLICER_OT_trim(bpy.types.Operator):
    """キワに沿ってビュー方向に貫通し、リボン側をまるごとトリム（削り落とし）"""
    bl_idname = "curve_slicer.trim"
    bl_label = "② トリム実行（ビュー方向に消去！）"
    bl_options = {'REGISTER', 'UNDO'}

    keep_cutter: bpy.props.BoolProperty(
        name="カッターを残す",
        description="トリム完了後もカッターを残すかどうか",
        default=False
    )

    def execute(self, context):
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        target_obj = get_target_mesh(context)
        cutter_obj = get_cutter_object(context)

        if not target_obj:
            self.report({'WARNING'}, "切断対象の立体（メッシュ）がありません。")
            return {'CANCELLED'}

        if not cutter_obj or "base_points" not in cutter_obj:
            self.report({'WARNING'}, "切断用のリボンカッターがありません。")
            return {'CANCELLED'}

        bbox_corners = [target_obj.matrix_world @ Vector(corner) for corner in target_obj.bound_box]
        size_x = max(c.x for c in bbox_corners) - min(c.x for c in bbox_corners)
        size_y = max(c.y for c in bbox_corners) - min(c.y for c in bbox_corners)
        size_z = max(c.z for c in bbox_corners) - min(c.z for c in bbox_corners)
        max_dim = max(size_x, size_y, size_z, 1.0)
        depth = max_dim * 4.0

        base_points = [Vector(p) for p in cutter_obj["base_points"]]
        normals = [Vector(n) for n in cutter_obj["normals"]]
        view_fwd = Vector(cutter_obj.get("view_fwd", [0, 0, -1]))
        flip_dir = cutter_obj.get("flip_dir", 1.0)
        width = context.scene.ribbon_height

        q_pts = [base_points[i] + normals[i] * (width * flip_dir) for i in range(len(base_points))]

        bm = bmesh.new()

        v_kf = [bm.verts.new(base_points[i] - view_fwd * depth) for i in range(len(base_points))]
        v_kb = [bm.verts.new(base_points[i] + view_fwd * depth) for i in range(len(base_points))]
        v_qf = [bm.verts.new(q_pts[i] - view_fwd * depth) for i in range(len(base_points))]
        v_qb = [bm.verts.new(q_pts[i] + view_fwd * depth) for i in range(len(base_points))]

        bm.verts.ensure_lookup_table()

        n_seg = len(base_points) - 1

        for i in range(n_seg):
            bm.faces.new([v_kf[i], v_kf[i+1], v_kb[i+1], v_kb[i]])
        for i in range(n_seg):
            bm.faces.new([v_qf[i], v_qb[i], v_qb[i+1], v_qf[i+1]])
        for i in range(n_seg):
            bm.faces.new([v_kf[i], v_qf[i], v_qf[i+1], v_kf[i+1]])
        for i in range(n_seg):
            bm.faces.new([v_kb[i], v_kb[i+1], v_qb[i+1], v_qb[i]])
        bm.faces.new([v_kf[0], v_kb[0], v_qb[0], v_qf[0]])
        bm.faces.new([v_kf[-1], v_qf[-1], v_qb[-1], v_kb[-1]])

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

        temp_mesh = bpy.data.meshes.new("Temp_Trim_Mesh")
        bm.to_mesh(temp_mesh)
        bm.free()

        trim_cutter_obj = bpy.data.objects.new("Temp_Trim_Cutter", temp_mesh)
        context.collection.objects.link(trim_cutter_obj)

        context.view_layer.objects.active = target_obj
        target_obj.select_set(True)

        bool_mod = target_obj.modifiers.new(name="View_Trim", type='BOOLEAN')
        bool_mod.object = trim_cutter_obj
        bool_mod.operation = 'DIFFERENCE'
        bool_mod.solver = 'EXACT'

        bpy.ops.object.modifier_apply(modifier=bool_mod.name)

        bpy.data.objects.remove(trim_cutter_obj, do_unlink=True)

        if not self.keep_cutter and cutter_obj.name.startswith("Slicer_Cutter"):
            bpy.data.objects.remove(cutter_obj, do_unlink=True)

        self.report({'INFO'}, "★ビュー方向へのトリムが完了しました！")
        return {'FINISHED'}


class CURVESLICER_PT_main_panel(bpy.types.Panel):
    """3Dビューのサイドバーに表示されるパネル"""
    bl_label = "Curve View Trimmer"
    bl_idname = "CURVESLICER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Curve Slicer'

    def draw(self, context):
        layout = self.layout

        # 手順1
        box1 = layout.box()
        box1.label(text="【手順1】ビュー視点で描く", icon='GREASEPENCIL')
        box1.label(text="※ Dキー+ドラッグで線を描く", icon='INFO')
        
        col1 = box1.column(align=True)
        col1.scale_y = 1.2
        col1.operator("curve_slicer.convert_annotation", text="① ペンの線をリボン化", icon='MOD_CURVE')
        col1.operator("curve_slicer.flip_direction", text="🔄 消す向きを反転 (Flip)", icon='FILE_REFRESH')

        box1.separator()
        box1.prop(context.scene, "ribbon_height", text="リボンの幅 (太さ)", slider=True)

        layout.separator()

        # 手順2
        box2 = layout.box()
        box2.label(text="【手順2】ビュー方向トリム", icon='MOD_BOOLEAN')
        col2 = box2.column(align=True)
        col2.scale_y = 1.5
        col2.operator("curve_slicer.trim", text="② トリム実行（ビュー方向に消去！）", icon='MOD_BOOLEAN')

        layout.separator()

        # ★一番下に配置したリセットボタン
        layout.operator("curve_slicer.clear_annotation", text="🗑️ ペン線を消す / リセット", icon='TRASH')


classes = (
    CURVESLICER_OT_convert_annotation,
    CURVESLICER_OT_flip_direction,
    CURVESLICER_OT_clear_annotation,
    CURVESLICER_OT_trim,
    CURVESLICER_PT_main_panel,
)

def register():
    bpy.types.Scene.ribbon_height = bpy.props.FloatProperty(
        name="リボンの幅",
        description="リボンの幅（太さ）",
        default=2.0,
        min=0.01,
        max=50.0,
        soft_max=10.0,
        unit='LENGTH',
        update=on_ribbon_width_update
    )
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene, "ribbon_height"):
        del bpy.types.Scene.ribbon_height

if __name__ == "__main__":
    register()