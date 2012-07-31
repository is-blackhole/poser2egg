poser2egg
=========

Exporter from Poser to Panda3d egg format.


Based on original code of user [satori](http://www.panda3d.org/forums/profile.php?mode=viewprofile&u=3839 "Satori") at Panda3d.org forum.

Supported features
--------
* Exporting mesh 

  Only Poser Figures supported now
  Export vertices (normals + uv), polygons

* Exporting textures and materials
 
  Can export diffuse, bump map (bump maps are not panda3d normal maps and need conversion to work)


  Texture files are not exported themself, you must make them available for panda3d via copying or egg postprocessing
* Exporting Joints
* Baking Poser morphs into mesh (experimental)
 
Resulting egg file usually need to be postprocessed by panda3d utils like egg-trans or egg-optchar

Postprocesing
--------
In order to some advanced panda3d features to work resulting egg must be postprocessed


**egg-trans -nv 90 -tbnall in.egg -o out.egg** will recalculate normals and tangent/binormals (poser files can have incorrect normals data; tangent/binormal required by panda3d normal mapping to work) 
