bl_info = {
    "name": "ZoneFbx Blender Plugin",
    "author": "Frey",
    "description": "Blender plugin to automate the process of blending textures for maps exported by ZoneFbx.",
    "version": (0, 1, 1),
    "location": "View3D > ZoneFbx",
    "blender": (2, 80, 0),
    "category": "Object",
}

import textwrap
import bpy

from os import path, sep
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty


class ZoneFbxBlendTexturesPanel(bpy.types.Panel):
    bl_label = "ZoneFbx"
    bl_idname = "OBJECT_PT_zonefbx_blend_textures"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ZoneFbx"

    def draw(self, context):
        layout = self.layout
        toImport = layout.box()
        wrap_text(toImport, "Import an FBX file from ZoneFbx")
        toImport.operator(ZoneFbxImport.bl_idname)

        alreadyImported = layout.box()
        wrap_text(
            alreadyImported,
            "Already imported the FBX file? Pick the folder with the corresponding textures:",
        )
        alreadyImported.operator(ZoneFbxBlendTextures.bl_idname)


class ZoneFbxBlendTextures(bpy.types.Operator, ImportHelper):
    bl_idname = "zonefbx.blend_textures"
    bl_label = "Choose Textures Folder"
    bl_description = (
        "Add mix nodes to all materials which have the corresponding custom properties"
    )

    directory: StringProperty()

    filter_glob: StringProperty(
        default="",
        options={"HIDDEN"},
        maxlen=255,
    )

    def execute(self, context):
        sanitized_directory = sanitize_directory(self, self.directory)
        if not sanitized_directory:
            return {"CANCELLED"}

        return blend_all_materials(sanitized_directory)


class ZoneFbxImport(bpy.types.Operator, ImportHelper):
    bl_idname = "zonefbx.import"
    bl_label = "Import FBX file"
    bl_description = "Import an FBX file from ZoneFbx and blend all relevant textures"

    filter_glob: StringProperty(
        default="*.fbx",
        options={"HIDDEN"},
        maxlen=255,
    )

    def execute(self, context):
        if not path.exists(self.filepath):
            self.report({"ERROR"}, "File does not exist")
            return {"CANCELLED"}

        sanitized_directory = sanitize_directory(self, path.dirname(self.filepath))
        if not sanitized_directory:
            return {"CANCELLED"}

        bpy.ops.import_scene.fbx(filepath=self.filepath)

        return blend_all_materials(sanitized_directory)


def wrap_text(element, full_text):
    wrap = textwrap.TextWrapper(width=50).wrap(text=full_text)
    for text in wrap:
        row = element.row(align=True)
        row.alignment = "EXPAND"
        row.label(text=text)


def blend_all_materials(directory):
    for material in bpy.data.materials:
        color_attribute_node = None
        if "BlendDiffuse" in material:
            color_attribute_node = blend_diffuse(
                material, directory, color_attribute_node
            )
        # Commenting out for now cause it looks weird
        # if 'BlendNormal' in material:
        #     add_mix_node_normal(material)
        if "BlendSpecular" in material:
            color_attribute_node = blend_specular(
                material, directory, color_attribute_node
            )
        if "BlendEmissive" in material:
            color_attribute_node = blend_emissive(
                material, directory, color_attribute_node
            )
    return {"FINISHED"}


def sanitize_directory(self, directory, recursive=False):
    """
    Sanitizes the input to ensure it is a valid textures folder.
    Accepts the textures folder itself or the parent folder of the textures folder.
    """
    if not path.isdir(directory):
        self.report(
            {"ERROR"},
            "Directory is not the textures folder or does not contain a textures folder",
        )
        return False

    if directory.endswith(sep):
        directory = directory[:-1]

    if path.split(directory)[1] != "textures":
        if recursive:
            self.report({"ERROR"}, "Unable to find textures folder")
            return False
        directory = path.join(directory, "textures")
        return sanitize_directory(self, directory, True)
    return directory


def blend_diffuse(material, directory, color_attribute_node):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    main_texture_node = main_node.inputs["Base Color"].links[0].from_node
    return add_and_swap_nodes(
        tree,
        main_texture_node,
        main_node.inputs["Base Color"],
        material["BlendDiffuse"],
        directory,
        color_attribute_node,
    )


def blend_normal(material, directory, color_attribute_node):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    normal_map_node = main_node.inputs["Normal"].links[0].from_node
    main_texture_node = normal_map_node.inputs["Color"].links[0].from_node
    return add_and_swap_nodes(
        tree,
        main_texture_node,
        normal_map_node.inputs["Color"],
        material["BlendNormal"],
        directory,
        color_attribute_node,
    )


def blend_specular(material, directory, color_attribute_node):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    main_texture_node = main_node.inputs["Specular IOR Level"].links[0].from_node
    return add_and_swap_nodes(
        tree,
        main_texture_node,
        main_node.inputs["Specular IOR Level"],
        material["BlendSpecular"],
        directory,
        color_attribute_node,
    )


def blend_emissive(material, directory, color_attribute_node):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    main_texture_node = main_node.inputs["Emission Color"].links[0].from_node
    return add_and_swap_nodes(
        tree,
        main_texture_node,
        main_node.inputs["Emission Color"],
        material["BlendEmissive"],
        directory,
        color_attribute_node,
    )


def add_and_swap_nodes(
    tree, node_to_swap, parent_input, custom_property, directory, color_attribute_node
):
    """
    Blends the original texture with the texture pointed to by custom_property and does all the node swapping.
    """
    # Create the new nodes
    nodes = tree.nodes
    if color_attribute_node is None:
        color_attribute_node = nodes.new("ShaderNodeVertexColor")
        color_attribute_node.layer_name = "Attribute"
    mix_node = nodes.new("ShaderNodeMix")
    image_texture_node = nodes.new("ShaderNodeTexImage")

    # Set properties
    mix_node.data_type = "RGBA"
    secondary_texture_path = path.join(directory, custom_property)
    image_texture_node.image = bpy.data.images.load(secondary_texture_path)

    # Link all the nodes
    tree.links.new(color_attribute_node.outputs["Alpha"], mix_node.inputs["Factor"])
    tree.links.new(node_to_swap.outputs["Color"], mix_node.inputs["A"])
    tree.links.new(image_texture_node.outputs["Color"], mix_node.inputs["B"])
    tree.links.new(mix_node.outputs["Result"], parent_input)

    return color_attribute_node


def register():
    bpy.utils.register_class(ZoneFbxBlendTexturesPanel)
    bpy.utils.register_class(ZoneFbxImport)
    bpy.utils.register_class(ZoneFbxBlendTextures)


def unregister():
    bpy.utils.unregister_class(ZoneFbxBlendTextures)
    bpy.utils.unregister_class(ZoneFbxImport)
    bpy.utils.unregister_class(ZoneFbxBlendTexturesPanel)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
