import bpy

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty

bl_info = {
	"name": "MDL Importer",
	"description": "Imports Warcraft 3 models",
	"author": "Yellow",
	"version": (0,0,1),
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
					ret[label].append([int(v) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")])
				if label == "Vertices":
					ret[label].append([float(v) / 20.0 for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")])
				if label == "Normals":
					ret[label].append([float(v) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")])
				if label == "TVertices":
					ret[label].append([float(v) for v in self.file.readline().replace("{", "").replace("}", "").replace(",", "").strip().split(" ")])
		return ret
			
class MDLParser(Parser):
	def __init__(self, file):
		self.tokens = {
			"Version": VersionParser(file),
			"Model": None, # We only care about the model's name right now
			"Geoset": GeosetParser(file),
			#"Sequences": , "GlobalSequences", "Textures", "Materials", 
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
				
			line = self.file.readline()

		return self.mdl

class Importer(bpy.types.Operator, ImportHelper):
	bl_idname = "import_mesh.mdl"
	bl_label = "MDL (.mdl)"
	filename_ext = ".mdl"
	filter_glob = StringProperty(deafult="*.mdl", options={"HIDDEN"})
	
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
				
				verts = [v for v3 in geoset["Vertices"] for v in v3]
				
				mesh.vertices.add(len(verts) // 3)
				mesh.vertices.foreach_set("co", verts)
				
				faces = [f for ff in geoset["Faces"] for f in ff]
				
				mesh.tessfaces.add(len(faces) //3 )
				mesh.tessfaces.foreach_set("vertices", faces)
				
				norms = [n for n3 in geoset["Normals"] for n in n3]
				
				mesh.vertices.foreach_set("normal", norms)
				mesh.update()

		return

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