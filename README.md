MDL Importer
============

This is a simple Blender addon that allows the importing of WarCraft 3 model meshes.

Install
-------

Install it by going to 
```
File -> User Preferences -> Install from File..
```
in Blender, and then point it at the mdl-importer.py

Usage
-----

This imports .mdl files, so you will have to extract any .mdx files from Blizzard .mpq archives and then convert them into .mdl for the time.

Once the addon is installed, you can import by going to
```
File -> Import -> MDL (.mdl)
```
and then select your model file from there.

Now that textures have been mostly added in, you will need to extract the corresponding .blp files from the .mpq as well, and then convert them to .png. Keep them in the same relative locations that they are found in the .mpq (e.g. Textures/HeroBladeMaster.blp or Units/Undead/Ghoul/Ghoul.blp).

The script is set to use the ~/Desktop/WC3Data directory as the root of where the .blp and .mdl files are. But you can change this in the script somewhere if you like.

An example structure for loading a ghoul model would require:
```
~/Desktop/WC3Data/Units/Undead/Ghoul/Ghoul.png
~/Desktop/WC3Data/Units/Undead/Ghoul/Ghoul.mdl
~/Desktop/WC3Data/Textures/gutz.png
~/Desktop/WC3Data/Textures/Peasant.png
```
