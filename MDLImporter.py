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
	"version": (0,1,0),
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

class VersionParser(Parser):
	def parse(self, context):
		label, version = self.file.readline().replace(",", "").split(" ")
		if int(version) != 800:
			raise Exception("MDL file version not supported")

class GeosetParser(Parser):
	def __init__(self, file):
		self.tokens = ["Vertices", "Normals", "TVertices", "Faces", "MaterialID"]
		super(GeosetParser, self).__init__(file)

	def parse(self, context):
		ret = {}
		
		pars = 1
		while pars != 0:
			line = self.file.readline().strip()
			pars = self.check_pars(pars, line)
			
			label, *data = line.split(" ")
			if label not in self.tokens:
				continue
			
			if label == "MaterialID":
				ret[label] = data[0].replace(",", "")
				continue
			
			ret[label] = []
			
			if label == "Faces":
				self.file.readline()
				pars = self.check_pars(pars, line)
				
			for x in range(int(data[0])):
				if label == "Faces":
					[ret[label].append(int(v)) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
				if label == "Vertices":
					[ret[label].append(float(v) / 20.0)  for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
				if label == "Normals":
					[ret[label].append(float(v)) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
				if label == "TVertices":
					ret[label].append([float(v) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")])
					
		return ret

class TextureParser(Parser):
	def parse(self, context, count):
		ret = {}
		texture = 0
		pars = 1
		
		while texture < count:
			line = self.file.readline().strip()
			pars = self.check_pars(pars, line)
			label, *data = line.split(" ")
			
			if label != "Bitmap":
				continue
			
			ret[texture] = {}
			line = self.file.readline().replace(",", "").strip()

			while self.check_pars(pars, line) == pars:
				label, data = line.split(" ")
				
				if data == '""':
					ret[texture][label] = ""
				else:
					ret[texture][label] = data.replace('"', "")
					
				line = self.file.readline().replace(",", "").strip()
			
			pars = self.check_pars(pars, line)
			texture += 1
		
		return ret

class MaterialParser(Parser):
	def __init__(self, file):
		self.layer_parser = LayerParser(file)
		super(MaterialParser, self).__init__(file)

	def parse(self, context, count):
		ret = {}
		material = 0
		pars = 1

		line = self.file.readline().strip()
		pars = self.check_pars(pars, line)
		
		while material < count:
			label, *data = line.split(" ")
			
			if label == "Material":				
				ret[material] = {"Layers": {}}
				layer = 0
				
				line = self.file.readline().replace(",", "").strip()
				pars = self.check_pars(pars, line)
				
				while pars > 1:
					label, *data = line.replace(",", "").split(" ")
					
					if label == "Layer":
						ret[material]["Layers"][layer] = self.layer_parser.parse(context)
						layer += 1
						pars -= 1
					elif label == "ConstantColor":
						ret[material]["ConstantColor"] = True
						
					line = self.file.readline().strip()
					pars = self.check_pars(pars, line)
				
			material += 1
			line = self.file.readline().replace(",", "").strip()
			pars = self.check_pars(pars, line)	
					
		return ret

		
class LayerParser(Parser):
	def __init__(self, file):
		self.tokens = ["FilterMode", "Unshaded", "TextureID", "Alpha", "TwoSided", "Linear"]
		super(LayerParser, self).__init__(file)
		
	def parse(self, context):
		layer = {}
		pars = 1
		
		line = self.file.readline().replace(",", "").strip()
		pars = self.check_pars(pars, line)
		
		while pars > 0:
			label, *data = line.split(" ")

			if label == "static":
				label = data[0]
				data = data[1:]
			
			if label in self.tokens:			
				if label == "Alpha":
					layer["Alpha"] = {}	
					line = self.file.readline().replace(",", "").strip()
					pars = self.check_pars(pars, line)
					
					while pars > 1:
						label, *data = line.split(" ")
						
						layer["Alpha"][label] = data[0] if len(data) > 0 else True
					
						line = self.file.readline().replace(",", "").strip()
						pars = self.check_pars(pars, line)	
				else:
					layer[label] = data[0] if len(data) > 0 else True
			
			line = self.file.readline().replace(",", "").strip()
			pars = self.check_pars(pars, line)
		
		return layer
		
class MDLParser(Parser):
	def __init__(self, file):
		self.tokens = {
			"Version": VersionParser(file),
			"Model": None, # We only care about the model's name right now
			"Geoset": GeosetParser(file),
			"Textures": TextureParser(file),
			"Materials": MaterialParser(file)
			#"Sequences": , "GlobalSequences", 
			#"GeosetAnim", "Bone", "Helper", "Attachment", "PivotPoints"
		}
		self.mdl = {"Geosets": []}
		super(MDLParser, self).__init__(file)

	def parse(self, context):
		line = self.file.readline()
		while(line):
			label, *data = line.split(" ")
			
			if label not in self.tokens:
				line = self.file.readline()
				continue
				
			if label == "Model":
				self.mdl["Name"] = data[0].replace('"', "")
			elif label == "Geoset":
				self.mdl["Geosets"].append(self.tokens[label].parse(context))
			elif label == "Version":
				self.tokens["Version"].parse(context)
			elif label == "Textures":
				self.mdl["Textures"] = self.tokens[label].parse(context, int(data[0]))
			elif label == "Materials":
				self.mdl["Materials"] = self.tokens[label].parse(context, int(data[0]))
				
			line = self.file.readline()

		return self.mdl

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
			mdl = MDLParser(file).parse(context)
			
			textures = []
			materials = []
			objs = []
			
			bpy.context.scene.render.engine = "CYCLES"
			
			# Load in the textures
			for x in range(len(mdl["Textures"])):
				texture = mdl["Textures"][x]
				tex = None
				
				# There are some textures with no file path, these appear to be just solid colours instead
				if not texture["Image"]:
					if "ReplaceableId" not in texture:
						tex = "TRANSPARENT"
						
					elif texture["ReplaceableId"] == "1":
						tex = "PLAYER_COLOUR"
						
					elif texture["ReplaceableId"] == "2":
						tex = "HERO_GLOW"
						
				else:
					path = os.path.expanduser("~/Desktop/Work/" + texture["Image"].replace("blp", "png"))
					tex = bpy.data.images.load(path)
				
				textures.append(tex)
			
			# Create the materials
			for x in range(len(mdl["Materials"])):
				material = mdl["Materials"][x]
				mat = bpy.data.materials.new("TexMat")
				mat.use_nodes = True
				mat.game_settings.alpha_blend = "CLIP"
				
				nodes = mat.node_tree.nodes
				links = mat.node_tree.links
				
				tex_image = nodes.new("ShaderNodeTexImage")
				output = nodes["Material Output"]
				diffuse = nodes["Diffuse BSDF"]
				mix = nodes.new("ShaderNodeMixShader")
				blend_colour = None
				
				# This bit sorts out composing layers. The layer with team colour needs to have the colour mixed in
				# The layer without the team colours need to have transparency mixed in
				# The colour is just set to green by default right now, change it in the "default_value" RGBA tuples
				for layer_key in material["Layers"]:
					layer = material["Layers"][layer_key]
					tex = textures[int(layer["TextureID"])]
					
					if tex == "PLAYER_COLOUR" or tex == "HERO_GLOW":
						blend_colour = nodes.new("ShaderNodeBsdfDiffuse")
						blend_colour.inputs[0].default_value = (0.0, 1.0, 0.0, 1.0)
						continue
					
					tex_image.image = tex
					if not blend_colour:
						blend_colour = nodes.new("ShaderNodeBsdfTransparent")
						blend_colour.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
				
				links.new(tex_image.outputs[0], diffuse.inputs[0])
				links.new(tex_image.outputs[1], mix.inputs[0])
				links.new(blend_colour.outputs[0], mix.inputs[1])
				links.new(diffuse.outputs[0], mix.inputs[2])
				links.new(mix.outputs[0], output.inputs[0])
					
				materials.append(mat)
			
			# Load in the meshes, and UVs, and add the materials to the correct one
			for x in range(len(mdl["Geosets"])):
				geoset = mdl["Geosets"][x]
			
				mesh = bpy.data.meshes.new("%s%iMesh" % (mdl["Name"], x))
				obj = bpy.data.objects.new("%s%iMesh" % (mdl["Name"], x), mesh)
				obj.location = (0.0, 0.0, 0.0)
				bpy.context.scene.objects.link(obj)
				
				mesh.vertices.add(len(geoset["Vertices"]) // 3)
				mesh.vertices.foreach_set("co", geoset["Vertices"])
				
				mesh.tessfaces.add(len(geoset["Faces"]) // 3)
				mesh.tessfaces.foreach_set("vertices", geoset["Faces"])
				
				mesh.vertices.foreach_set("normal", geoset["Normals"])
				
				mesh.update()
				
				vi_uv = {i: (u, 1.0 - v) for i, (u, v) in enumerate(geoset["TVertices"])}
				per_loop_list = [0.0] * len(mesh.loops)
				for loop in mesh.loops:
					per_loop_list[loop.index] = vi_uv[loop.vertex_index]
				
				per_loop_list = [uv for pair in per_loop_list for uv in pair]
				
				mesh.uv_textures.new("UV")
				mesh.uv_layers[0].data.foreach_set("uv", per_loop_list)
				
				mat_id = int(geoset["MaterialID"])
				mesh.materials.append(materials[mat_id])
				
				mesh.update()
				
				objs.append(obj)

		return {"FINISHED"}

def menu(self, context):
	self.layout.operator("import_mesh.mdl", text="MDL (.mdl)")

def register():
	bpy.utils.register_class(Importer)
	bpy.types.INFO_MT_file_import.append(menu)
	
def unregister():
	bpy.utils.unregister_class(Importer)
	bpy.types.INFO_MT_file_import.remove(menu)
		
if __name__ == "__main__":
	register()
	
	bpy.ops.import_mesh.mdl("INVOKE_DEFAULT")