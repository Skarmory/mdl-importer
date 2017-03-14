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

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty

bl_info = {
	"name": "MDL Importer",
	"description": "Imports Warcraft 3 models",
	"author": "Yellow",
	"version": (0,0,2),
	"blender": (2,7,8),
	"location": "File > Import > MDL (.mdl)",
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
		self.tokens = ["Vertices", "Normals", "TVertices", "Faces"]
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
			
			ret[label] = []
			if label == "Faces":
				self.file.readline()
				
			for x in range(int(data[0])):
				if label == "Faces":
					[ret[label].append(int(v)) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
				if label == "Vertices":
					[ret[label].append(float(v) / 20.0)  for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
				if label == "Normals":
					[ret[label].append(float(v)) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
				if label == "TVertices":
					[ret[label].append(float(v)) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")]
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
				ret[material] = {}
				layer = 0
				
				line = self.file.readline().replace(",", "").strip()
				pars = self.check_pars(pars, line)
				
				while pars > 2:
					label, *data = line.replace(",", "").split(" ")
					
					if label == "Layer":
						ret[material][layer] = self.layer_parser.parse(context)
						layer += 1
					
					pars -= 1
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
						
						layer["Alpha"][label] = data[0] if len(data) > 0 else None
					
						line = self.file.readline().replace(",", "").strip()
						pars = self.check_pars(pars, line)	
				else:
					layer[label] = data[0] if len(data) > 0 else None
			
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