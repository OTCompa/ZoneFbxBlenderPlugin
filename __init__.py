bl_info = {
    "name": "ZoneFbx Blender Plugin",
    "author": "Frey",
    "description": "Blender plugin to automate the process of blending textures for maps exported by ZoneFbx.",
    "version": (0, 1, 0),
    "location": "View3D > ZoneFbx",
    "blender": (2, 80, 0),
    "category": "Object",
}

import bpy


class ZoneFbxBlendTexturesPanel(bpy.types.Panel):
    bl_label = "ZoneFbx"
    bl_idname = "OBJECT_PT_zonefbx_blend_textures"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ZoneFbx"

    def draw(self, context):
        layout = self.layout
        layout.operator(ZoneFbxBlendTextures.bl_idname)


class ZoneFbxBlendTextures(bpy.types.Operator):
    bl_idname = "zonefbx.blend_textures"
    bl_label = "ZoneFbx Blend Textures"

    def execute(self, context):
        for material in bpy.data.materials:
            color_attribute_node = None
            # TODO: add reused color attribute, set color attribute, position nodes properly
            if "BlendDiffuse" in material:
                color_attribute_node = blend_diffuse(material, color_attribute_node)
            # Commenting out for now cause it looks weird
            # if 'BlendNormal' in material:
            #     add_mix_node_normal(material)
            if "BlendSpecular" in material:
                color_attribute_node = blend_specular(material, color_attribute_node)
            if "BlendEmissive" in material:
                color_attribute_node = blend_emissive(material, color_attribute_node)
        return {"FINISHED"}


def blend_diffuse(material, color_attribute_node):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    main_texture_node = main_node.inputs["Base Color"].links[0].from_node
    return add_and_swap_nodes(
        tree,
        main_texture_node,
        main_node.inputs["Base Color"],
        material["BlendDiffuse"],
        color_attribute_node,
    )


def blend_normal(material, color_attribute_node):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    normal_map_node = main_node.inputs["Normal"].links[0].from_node
    main_texture_node = normal_map_node.inputs["Color"].links[0].from_node
    return add_and_swap_nodes(
        tree,
        main_texture_node,
        normal_map_node.inputs["Color"],
        material["BlendNormal"],
        color_attribute_node,
    )


def blend_specular(material, color_attribute_node):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    main_texture_node = main_node.inputs["Specular IOR Level"].links[0].from_node
    return add_and_swap_nodes(
        tree,
        main_texture_node,
        main_node.inputs["Specular IOR Level"],
        material["BlendSpecular"],
        color_attribute_node,
    )


def blend_emissive(material, color_attribute_node):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    main_texture_node = main_node.inputs["Emission Color"].links[0].from_node
    return add_and_swap_nodes(
        tree,
        main_texture_node,
        main_node.inputs["Emission Color"],
        material["BlendEmissive"],
        color_attribute_node,
    )


def add_and_swap_nodes(
    tree, node_to_swap, parent_input, custom_property, color_attribute_node
):
    nodes = tree.nodes
    if color_attribute_node is None:
        color_attribute_node = nodes.new("ShaderNodeVertexColor")
    mix_node = nodes.new("ShaderNodeMix")
    image_texture_node = nodes.new("ShaderNodeTexImage")

    mix_node.data_type = "RGBA"
    image_texture_node.image = bpy.data.images.load(custom_property)

    tree.links.new(color_attribute_node.outputs["Alpha"], mix_node.inputs["Factor"])
    tree.links.new(node_to_swap.outputs["Color"], mix_node.inputs["A"])
    tree.links.new(image_texture_node.outputs["Color"], mix_node.inputs["B"])

    tree.links.new(mix_node.outputs["Result"], parent_input)

    return color_attribute_node


def menu_func(self, context):
    self.layout.operator(ZoneFbxBlendTextures.bl_idname)


def register():
    bpy.utils.register_class(ZoneFbxBlendTexturesPanel)
    bpy.utils.register_class(ZoneFbxBlendTextures)


def unregister():
    bpy.utils.unregister_class(ZoneFbxBlendTextures)
    bpy.utils.unregister_class(ZoneFbxBlendTexturesPanel)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
