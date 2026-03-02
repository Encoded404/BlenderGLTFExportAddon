# __init__.py

import bpy
from typing import Optional

# -------------------------
# Scene properties
# -------------------------
class GLTFShaderIndexProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="Export shader index",
        description="Include material.shader_index / material.shader_name in glTF materials[].extras",
        default=True,
    )

    extras_key_prefix: bpy.props.StringProperty(
        name="Extras key prefix",
        description="Prefix to prepend to the extras key (empty = no prefix). Example: 'MY_' -> 'MY_shader_index'",
        default="",
    )


def draw_export(context, layout):
    """Small UI block to show in the glTF export panel (best-effort registration)."""
    scn = context.scene
    props = getattr(scn, "glTFShaderIndexProps", None)
    if props is None:
        layout.label(text="(Shader index extension not available)")
        return
    box = layout.box()
    box.prop(props, "enabled")
    box.prop(props, "extras_key_prefix", text="Extras prefix")


# -------------------------
# glTF export user-extension
# -------------------------
# The glTF exporter looks for a class named exactly `glTF2ExportUserExtension`
# and instantiates it during export. Keep that name.
class glTF2ExportUserExtension:
    def __init__(self):
        # Delay importing exporter internals until the exporter instantiates this class.
        # (The exporter may not be loaded at addon registration time.)
        try:
            from io_scene_gltf2.io.com.gltf2_io_extensions import Extension  # type: ignore
            self.Extension = Extension
        except Exception:
            self.Extension = None

        # Cache scene properties; fallback to None if scene not available.
        try:
            self.props: Optional[GLTFShaderIndexProperties] = bpy.context.scene.glTFShaderIndexProps
        except Exception:
            self.props = None

        # If you ever produce a real glTF extension object, set this accordingly.
        self.is_critical = False

    def gather_material_hook(self, gltf2_material, blender_material, export_settings):
        """
        Called by exporter for each material. Writes shader_index/shader_name
        from Blender material custom properties into gltf2_material.extras.
        """
        if not self.props or not self.props.enabled:
            return
        if blender_material is None:
            return

        shader_index = None
        shader_name = None

        if "shader_index" in blender_material:
            try:
                shader_index = int(blender_material["shader_index"])
            except Exception:
                try:
                    shader_index = int(float(blender_material["shader_index"]))
                except Exception:
                    shader_index = None

        if "shader_name" in blender_material:
            try:
                shader_name = str(blender_material["shader_name"]) if blender_material["shader_name"] is not None else None
            except Exception:
                shader_name = None

        if shader_index is None and shader_name is None:
            return

        if getattr(gltf2_material, "extras", None) is None:
            gltf2_material.extras = {}

        prefix = self.props.extras_key_prefix or ""

        if shader_index is not None:
            gltf2_material.extras[f"{prefix}shader_index"] = shader_index
        if shader_name is not None:
            gltf2_material.extras[f"{prefix}shader_name"] = shader_name

    def gather_node_hook(self, gltf2_node, blender_object, export_settings):
        """
        Optional: write shader metadata stored on blender objects into node.extras.
        """
        if not self.props or not self.props.enabled:
            return
        if blender_object is None:
            return
        if "shader_index" not in blender_object and "shader_name" not in blender_object:
            return

        if getattr(gltf2_node, "extras", None) is None:
            gltf2_node.extras = {}

        prefix = self.props.extras_key_prefix or ""

        if "shader_index" in blender_object:
            try:
                val = int(blender_object["shader_index"])
                gltf2_node.extras[f"{prefix}shader_index"] = val
            except Exception:
                pass

        if "shader_name" in blender_object:
            try:
                gltf2_node.extras[f"{prefix}shader_name"] = str(blender_object["shader_name"])
            except Exception:
                pass


# -------------------------
# Registration
# -------------------------
classes = (
    GLTFShaderIndexProperties,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.glTFShaderIndexProps = bpy.props.PointerProperty(type=GLTFShaderIndexProperties)

    # Best-effort: register a small draw callback inside the glTF export UI.
    # The glTF exporter publishes `exporter_extension_layout_draw` (a dict) which
    # add-ons can populate. That module may not be importable at register time,
    # so guard the import.
    try:
        from io_scene_gltf2 import exporter_extension_layout_draw  # type: ignore
        exporter_extension_layout_draw["io_gltf_shader_index"] = draw_export
    except Exception:
        # exporter not present right now; it's OK — the exporter will still
        # detect glTF2ExportUserExtension at export time.
        pass


def unregister():
    try:
        from io_scene_gltf2 import exporter_extension_layout_draw  # type: ignore
        if "io_gltf_shader_index" in exporter_extension_layout_draw:
            del exporter_extension_layout_draw["io_gltf_shader_index"]
    except Exception:
        pass

    try:
        del bpy.types.Scene.glTFShaderIndexProps
    except Exception:
        pass

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


# allow direct run while editing in Blender's Text Editor
if __name__ == "__main__":
    register()