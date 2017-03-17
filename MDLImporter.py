#Copyright 2017 Yellow
#
#Permission is hereby granted, free of charge, to any person obtaining a copy 
#of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights 
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
#copies of the Software, and to permit persons to whom the Software is furnished
#to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all 
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
#INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
#PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
#OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
#DEALINGS IN THE SOFTWARE.

import bpy
import os

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty

bl_info = {
	"name": "MDL Importer",
	"description": "Imports Warcraft 3 models",
	"author": "Yellow",
	"version": (0,1,5),
	"blender": (2,7,8),
	"location": "File > Import > WC3 MDL (.mdl)",
	"category": "Import-Export"
}

class Parser(object):
	def __init__(self, file):
		self.file = file
		
	def parse(self, context):
		pass
			
	def check_pars(self, pars, line):
		line.strip('\n')
		if line.endswith("{"):
			pars += 1
		elif line.endswith("}"):
			pars -= 1
		return pars
	
	def read(self, pars):
		line = self.file.readline().replace(",", "").strip()
		pars = self.check_pars(pars, line)
		return line, pars

class VersionParser(Parser):
	def parse(self, context):
		label, version = self.file.readline().replace(",", "").split(" ")
		if int(version) != 800:
			raise Exception("MDL file version not supported")

			
class Geoset(object):
	def __init__(self):
		self.vertices = []
		self.normals = []
		self.faces = []
		self.uvs = []
		self.material_id = None
		
class GeosetParser(Parser):
	def __init__(self, file):
		self.tokens = ["Vertices", "Normals", "TVertices", "Faces", "MaterialID"]
		super(GeosetParser, self).__init__(file)

	def parse(self, context):
		geoset = Geoset()
		pars = 1
		
		line = self.file.readline().strip()
		pars = self.check_pars(pars, line)
		
		while pars > 0:
			label, *data = line.split(" ")
			
			if label in self.tokens:
				if label == "MaterialID":
					geoset.material_id = int(data[0].replace(",", ""))
					
				elif label in ["Vertices", "Normals", "Faces", "TVertices"]:
					
					if label == "Vertices":
						for _ in range(int(data[0])):
							[geoset.vertices.append(float(v) / 20.0)  for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
							
					elif label == "Normals":
						for _ in range(int(data[0])):
							[geoset.normals.append(float(v)) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
							
					elif label == "Faces":
						line, pars = self.read(pars)
						[geoset.faces.append(int(v)) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
						line, pars = self.read(pars)
						
					elif label == "TVertices":
						for _ in range(int(data[0])):
							geoset.uvs.append([float(v) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")])
						
			line = self.file.readline().strip()
			pars = self.check_pars(pars, line)
					
		return geoset

class Texture(object):
	def __init__(self):
		self.filepath = ""
		self.replaceable_id = None
		
class TextureParser(Parser):
	def parse(self, context, count):
		textures = []
		pars = 1
		
		line, pars = self.read(pars)
		
		for _ in range(count):
			label, *data = line.split(" ")
			
			if label == "Bitmap":
				texture = Texture()
				textures.append(texture)
				
				line, pas = self.read(pars)

				while pars > 1:
					label, data = line.split(" ")
					
					if label == "Image" and data:
						texture.filepath = data.replace('"', "").replace("blp", "png")
					elif label == "ReplaceableId":
						texture.replaceable_id = int(data)
					else:
						raise Exception("Unknown data in texture: %s %s" % (label, data))
						
					line, pars = self.read(pars)
				
				if texture.replaceable_id == 2:
					texture.filepath = "ReplaceableTextures/TeamGlow/TeamGlow00.png"
				
			line, pars = self.read(pars)
		
		return textures

class Material(object):
	FLAGS = {"ConstantColor": 2**0, "SortPrimitivesNearZ": 2**3, "SortPrimitivesFarZ": 2**4, "FullResolution": 2**5}
	def __init__(self):
		self.layers = []
		self.flags = 0
		
class MaterialParser(Parser):
	def __init__(self, file):
		self.layer_parser = LayerParser(file)
		super(MaterialParser, self).__init__(file)

	def parse(self, context, count):
		materials = []
		pars = 1

		line, pars = self.read(pars)
		
		for _ in range(count):
			label, *data = line.split(" ")
			
			if label == "Material":	
				material = Material()
				materials.append(material)
				
				line, pars = self.read(pars)
				
				while pars > 1:
					label, *data = line.split(" ")
					
					if label == "Layer":
						material.layers.append(self.layer_parser.parse(context))
						pars -= 1
					elif label in Material.FLAGS:
						material.flags |= Material.FLAGS[label]
					else:
						raise Exception("Unknown data in material: %s %s" % (label, data))
						
					line, pars = self.read(pars)
				
			line, pars = self.read(pars)
					
		return materials

class Layer(object):
	SHADING_FLAGS = {"Unshaded": 2**0, "SphereEnvironmentMap": 2**1, "TwoSided": 2**4, "Unfogged": 2**5, "NoDepthTest": 2**6, "NoDepthSet": 2**7}
	FILTER_MODES = ["None", "Transparent", "Blend", "Additive", "AddAlpha", "Modulate", "Modulate2x"]
	def __init__(self):
		self.filter_mode 		 = "None"
		self.shading_flags 		 = 0
		self.texture_id 		 = None
		self.texture_anim_id 	 = None
		self.coord_id 			 = None
		self.alpha 				 = None
		self.material_alpha      = None
		self.material_texture_id = None

class MaterialAlpha(object):
	def __init__(self):
		self.interpolation_type = "None"
		self.tracks				= {}

class LayerParser(Parser):
	def __init__(self, file):
		self.tokens = [
			"FilterMode", "Unshaded", "SphereEnvironmentMap", 
			"TwoSided", "Unfogged", "NoDepthTest", "NoDepthSet",
			"TextureID", "Alpha", "Linear"
		]
		super(LayerParser, self).__init__(file)
		
	def parse(self, context):
		layer = Layer()
		pars = 1
		
		line, pars = self.read(pars)
		
		while pars > 0:
			label, *data = line.split(" ")

			if label == "static":
				label = data[0]
				data = data[1:]
			
			if label in self.tokens:			
				if label in Layer.SHADING_FLAGS:
					layer.shading_flags |= Layer.SHADING_FLAGS[label]
					
				elif label == "FilterMode":
					if data[0] in Layer.FILTER_MODES:
						layer.filter_mode = data[0]
					else:
						raise Exception("Unknown FilterMode: '%s'" % data[0])
					
				elif label == "Alpha":
					if len(data) > 1:
						layer.material_alpha = MaterialAlpha()
						
						line, pars = self.read(pars)
					
						while pars > 1:
							label, *data = line.replace(":", "").strip().split(" ")
							
							if label in ["Linear", "Hermite", "Bezier", "DontInterp"]:
								layer.material_alpha.interpolation_type = label
							else:
								layer.material_alpha.tracks[label] = data[0]
					
							line, pars = self.read(pars)	
					else:
						layer.alpha = data[0]
						
				elif label == "TextureID":
					layer.texture_id = int(data[0])
			else:
				raise Exception("Unknown data in layer: %s %s" % (label, data))
				
			line, pars = self.read(pars)
		
		return layer

class Model(object):
	def __init__(self):
		self.name = ""
		self.geosets = []
		self.textures = []
		self.materials = []
		
class MDLParser(Parser):
	def __init__(self, file):
		self.tokens = {
			"Version": VersionParser(file),
			"Model": None, # We only care about the model's name right now
			"Geoset": GeosetParser(file),
			"Textures": TextureParser(file),
			"Materials": MaterialParser(file)
			#"Sequences": , 
			#"GlobalSequences", 
			#"GeosetAnim", 
			#"Bone", 
			#"Helper", 
			#"Attachment", 
			#"PivotPoints"
		}
		super(MDLParser, self).__init__(file)

	def parse(self, context):
		model = Model()
		line = self.file.readline()
		while(line):
			label, *data = line.split(" ")
			
			if label not in self.tokens:
				line = self.file.readline()
				continue
				
			if label == "Model":
				model.name = data[0].replace('"', "")
			elif label == "Geoset":
				model.geosets.append(self.tokens[label].parse(context))
			elif label == "Version":
				self.tokens["Version"].parse(context)
			elif label == "Textures":
				model.textures = self.tokens[label].parse(context, int(data[0]))
			elif label == "Materials":
				model.materials = self.tokens[label].parse(context, int(data[0]))
				
			line = self.file.readline()

		return model

class Importer(bpy.types.Operator, ImportHelper):
	bl_idname = "import_mesh.mdl"
	bl_label = "MDL (.mdl)"
	filename_ext = ".mdl"
	filter_glob = StringProperty(default="*.mdl", options={"HIDDEN"})
	
	@classmethod
	def poll(cls, context):
		return True
		
	def execute(self, context):
	
		with open(self.filepath, "r") as file:
			model = MDLParser(file).parse(context)
			
			textures = []
			materials = []
			objs = []
			
			# Make blender set the viewport shading to "Material" so we can see something
			bpy.context.scene.render.engine = "CYCLES"
			for area in bpy.context.screen.areas:
				if area.type == "VIEW_3D":
					for space in area.spaces:
						if space.type == "VIEW_3D":
							space.viewport_shade = "MATERIAL"
			
			# Create the materials
			for i, material in enumerate(model.materials):

				mat = bpy.data.materials.new("%s Material %i" % (model.name, i))
				mat.use_nodes = True
				mat.game_settings.alpha_blend = "CLIP"
				
				nodes = mat.node_tree.nodes
				links = mat.node_tree.links
				
				tex_image = nodes.new("ShaderNodeTexImage")
				output = nodes["Material Output"]
				diffuse = nodes["Diffuse BSDF"]
				mix = nodes.new("ShaderNodeMixShader")
				blend_colour = None
				rid = None
				
				# This bit sorts out composing layers. The layer with team colour needs to have the colour mixed in
				# The layer without the team colours need to have transparency mixed in
				# The colour is just set to green by default right now, change it in the "default_value" RGBA tuples
				for layer in material.layers:
					tex = model.textures[layer.texture_id]
					rid = tex.replaceable_id
					
					if rid == 1:
						blend_colour = nodes.new("ShaderNodeBsdfDiffuse")
						blend_colour.inputs[0].default_value = (0.0, 1.0, 0.0, 1.0)
						continue
					elif rid == 2:
						nodes.remove(diffuse)
						diffuse = nodes.new("ShaderNodeEmission")
						diffuse.inputs[0].default_value = (0.0, 1.0, 0.0, 1.0)
					
					tex_image.image = bpy.data.images.load(os.path.expanduser("~/Desktop/WC3Data/" + tex.filepath))
					if not blend_colour:
						blend_colour = nodes.new("ShaderNodeBsdfTransparent")
						if rid == 2:
							blend_colour.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
						else:
							blend_colour.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
				
				if rid == 2:
					links.new(tex_image.outputs[0], mix.inputs[0])
				else:
					links.new(tex_image.outputs[0], diffuse.inputs[0])
					links.new(tex_image.outputs[1], mix.inputs[0])
					
				links.new(blend_colour.outputs[0], mix.inputs[1])
				links.new(diffuse.outputs[0], mix.inputs[2])
				links.new(mix.outputs[0], output.inputs[0])
					
				materials.append(mat)
			
			# Load in the meshes, and UVs, and add the materials to the correct one
			for i, geoset in enumerate(model.geosets):
			
				mesh = bpy.data.meshes.new("%s Mesh %i" % (model.name, i))
				obj = bpy.data.objects.new("%s Mesh %i" % (model.name, i), mesh)
				obj.location = (0.0, 0.0, 0.0)
				bpy.context.scene.objects.link(obj)
				
				mesh.vertices.add(len(geoset.vertices) // 3)
				mesh.vertices.foreach_set("co", geoset.vertices)
				
				mesh.tessfaces.add(len(geoset.faces) // 3)
				mesh.tessfaces.foreach_set("vertices", geoset.faces)
				
				mesh.vertices.foreach_set("normal", geoset.normals)
				
				mesh.update()
				
				vi_uv = {i: (u, 1.0 - v) for i, (u, v) in enumerate(geoset.uvs)}
				per_loop_list = [0.0] * len(mesh.loops)
				for loop in mesh.loops:
					per_loop_list[loop.index] = vi_uv[loop.vertex_index]
				
				per_loop_list = [uv for pair in per_loop_list for uv in pair]
				
				mesh.uv_textures.new("UV")
				mesh.uv_layers[0].data.foreach_set("uv", per_loop_list)
				
				mesh.materials.append(materials[geoset.material_id])
				
				mesh.update()
				
				objs.append(obj)

		return {"FINISHED"}

def menu(self, context):
	self.layout.operator("import_mesh.mdl", text="WC3 MDL (.mdl)")

def register():
	bpy.utils.register_class(Importer)
	bpy.types.INFO_MT_file_import.append(menu)
	
def unregister():
	bpy.utils.unregister_class(Importer)
	bpy.types.INFO_MT_file_import.remove(menu)
		
if __name__ == "__main__":
	register()
	
	bpy.ops.import_mesh.mdl("INVOKE_DEFAULT")