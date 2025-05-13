bl_info = {
    "name": "ZoneFbx Blender Plugin",
    "blender": (2, 80, 0),
    "category": "Object",
}

import bpy
import logging

log = logging.getLogger(__name__)


class ObjectMoveX(bpy.types.Operator):
    bl_idname = "zonefbx.test"
    bl_label = "ZoneFbx test"

    def execute(self, context):
        for material in bpy.data.materials:
            if "BlendDiffuse" in material:
                add_mix_node(material)
            # Commenting out for now cause it looks weird
            # if 'BlendNormal' in material:
            #     add_mix_node_normal(material)
            if "BlendSpecular" in material:
                add_mix_node_specular(material)
            if "BlendEmissive" in material:
                add_mix_node_emissive(material)
        return {"FINISHED"}


def add_mix_node(material):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    main_texture_node = main_node.inputs["Base Color"].links[0].from_node
    add_and_swap_nodes(
        tree,
        main_texture_node,
        main_node.inputs["Base Color"],
        material["BlendDiffuse"],
    )


def add_mix_node_normal(material):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    normal_map_node = main_node.inputs["Normal"].links[0].from_node
    main_texture_node = normal_map_node.inputs["Color"].links[0].from_node
    add_and_swap_nodes(
        tree,
        main_texture_node,
        normal_map_node.inputs["Color"],
        material["BlendNormal"],
    )


def add_mix_node_specular(material):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    main_texture_node = main_node.inputs["Specular IOR Level"].links[0].from_node
    add_and_swap_nodes(
        tree,
        main_texture_node,
        main_node.inputs["Specular IOR Level"],
        material["BlendSpecular"],
    )


def add_mix_node_emissive(material):
    tree = material.node_tree
    main_node = tree.nodes["Principled BSDF"]
    main_texture_node = main_node.inputs["Emission Color"].links[0].from_node
    add_and_swap_nodes(
        tree,
        main_texture_node,
        main_node.inputs["Emission Color"],
        material["BlendEmissive"],
    )


def add_and_swap_nodes(tree, node_to_swap, parent_input, custom_property):
    nodes = tree.nodes
    colorAttributeNode = nodes.new("ShaderNodeVertexColor")
    mixNode = nodes.new("ShaderNodeMix")
    image_texture_node = nodes.new("ShaderNodeTexImage")

    mixNode.data_type = "RGBA"
    image_texture_node.image = bpy.data.images.load(custom_property)

    tree.links.new(colorAttributeNode.outputs["Alpha"], mixNode.inputs["Factor"])
    tree.links.new(node_to_swap.outputs["Color"], mixNode.inputs["A"])
    tree.links.new(image_texture_node.outputs["Color"], mixNode.inputs["B"])

    tree.links.new(mixNode.outputs["Result"], parent_input)


def menu_func(self, context):
    self.layout.operator(ObjectMoveX.bl_idname)


def register():
    bpy.utils.register_class(ObjectMoveX)
    bpy.types.VIEW3D_MT_object.append(
        menu_func
    )  # Adds the new operator to an existing menu.


def unregister():
    bpy.utils.unregister_class(ObjectMoveX)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
