############################################################
#
# poser2egg.py - Egg File Exporter for Poser Pro
#
# Version 0.1 - Current only exports vertex positions
# and normals. joints are exported, but there are still some
# issues. It currently doesnt export UV coords, textures,
# materials, morphs, weights or animation data, but i have
# plans for all of those.
#
# Run this script inside the Poser in the PoserPython
# interpreter. You should also have Panda3d installed
# on the system. I have only tested it on windows vista
# with Panda3D 1.6.2
# Author: satori(http://www.panda3d.org/forums/profile.php?mode=viewprofile&u=3839), v 0.1
# Author: is_blackhole
#
############################################################
import poser
import os
import string

V4_RELATIVE_TEXTURE_PATH = False
############################################################
# General Functions
############################################################


# some code from chicken exporter
def egg_safe_same(s):
    """Function that converts names into something suitable for the egg file format - simply puts " around names that contain spaces and prunes bad characters, replacing them with an underscore."""
    s = s.replace('"', '_')  # Sure there are more bad characters, but this will do for now.
    if ' ' in s:
        return '"' + s + '"'
    else:
        return s


def indent_string(string, level):
    # indent size is 2 chars
    return string.rjust(len(string) + (level * 2))


def fix_name(name):
    # currently only removes spaces
    return name.replace(" ", "")


def vec_subtract(v1, v2):
    return v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]


def get_matrix(t):
    return ((1, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 1, 0),
            (t[0], t[1], t[2], 1))

############################################################
# Egg Writing Functions
############################################################


def write_comment(comment, level):
    r = [indent_string('<Comment> {\n', level)]
    for ln in comment.splitlines():
        r.append(indent_string('"%s"' % ln, level + 1))
    r.append(indent_string('\n}\n', level))
    return string.join(r)


def write_transform(matrix, level):
    r = [indent_string('<Transform> {\n', level)]
    r += indent_string('<Matrix4> {\n', level + 1)
    for row in matrix:
        s = " ".join([str(f) for f in row])
        r.append(indent_string(s, level + 2))
        r.append('\n')
    r.append(indent_string('}\n', level + 1))
    r.append(indent_string('}\n', level))
    return r


class TextureMode:
    MODULATE = 'MODULATE'
    ADD = 'ADD'
    NORMAL = 'NORMAL'
    GLOSS = 'GLOSS'
    HEIGHT = 'HEIGHT'


class EggMaterial:
    def __init__(self, poser_material):
        self.poser_material = poser_material
        self.name = egg_safe_same(poser_material.Name())

        textures = [self._check_texture(poser_material.TextureMapFileName(), '_texture', TextureMode.MODULATE),
                   self._check_texture(poser_material.BumpMapFileName(), '_bump', TextureMode.NORMAL)]
                   #self._check_texture(poser_material.TransparencyMapFileName(), '_transparency', TextureMode.MODULATE)
        self.textures = filter(None, textures)

    def _check_texture(self, textureName, egg_texture_name, egg_texture_mode):
        texture = EggTexture(textureName, self.name + egg_texture_name, egg_texture_mode)
        return texture.check_texture()

    def write(self):
        lines = ["<Material> %s {\n" % self.name]
        lines += "   <Scalar> diffr {%f} <Scalar> diffg {%f} <Scalar> diffb {%f}\n" % (self.poser_material.DiffuseColor())
        sr, sg, sb = self.poser_material.SpecularColor()
        lines += "   <Scalar> specr {%f} <Scalar> specg {%f} <Scalar> specb {%f}\n" % (sr * 0.2, sg * 0.2, sb * 0.2)
        lines += "   <Scalar> shininess { 25 }"
        lines += "\n}\n"
        return lines

    def __str__(self):
        return self.name + ",".join(self.textures)


class EggTexture:
    EMPTY_TEXTURE = poser.ContentRootLocation().replace("\\", '/').replace(":", "")
    ALL_TEXTURES = {}

    def __init__(self, filename, texture_name, texture_mode):
        self.texture_mode = texture_mode
        self.filename = None
        if filename is not None:
            self.filename = filename.replace("\\", '/').replace(":", "")
            if V4_RELATIVE_TEXTURE_PATH:
                head, tail = os.path.split(self.filename)
                self.filename = os.path.join(head.split('/')[-1], tail)
        self.name = egg_safe_same(texture_name)

    def check_texture(self):
        if self.filename != EggTexture.EMPTY_TEXTURE and self.filename is not None:
            if self.filename not in EggTexture.ALL_TEXTURES:
                EggTexture.ALL_TEXTURES[self.filename] = self
            return EggTexture.ALL_TEXTURES[self.filename].name
        return None

    def write(self):
        lines = ["<Texture> %s {\n \"%s\" \n" % (self.name, self.filename)]
        lines += "   <Scalar> envtype { %s }" % self.texture_mode
        lines += "   <Scalar> wrap { %s }" % 'CLAMP'
        lines += "\n}\n"
        return lines


class EggObject:
    empty_texture = poser.ContentRootLocation()
    SKIP_MORPHS = 'SKIP_MORPHS'
    BAKE_MORPHS = 'BAKE_MORPHS'
    EXPORT_MORPHS = 'EXPORT_MORPHS'

    def __init__(self, figure):
        self.options = {"morph": self.BAKE_MORPHS, "textures": True}
        self.figure = figure
        self.figure_name = fix_name(figure.Name())

    def export(self):
        # get geometry from poser
        uniGeometry, self.uniActorList, self.uniActorVertexInfoList = self.figure.UnimeshInfo()
        # collect materials/textures
        self.materials, self.textures = self.collect_materials(self.figure)
        # collect vertices
        self.vertices, self.polygons, self.poser2egg = self.collect_vertices(self.uniActorList)
        # collect joints
        self.joints = self.collect_joints(self.figure.ParentActor(), 1)
        # write egg content
        return self.write()

    def collect_joints(self, actor, level):
        if not actor.IsBodyPart():
            return
        actorName = fix_name(actor.Name())
        print indent_string('processing %s' % actorName, level)
        origin = actor.Origin()
        parentOrigin = actor.Parent().Origin()
        if actor.Name() == self.figure.ParentActor().Name():
            matrix = get_matrix(get_matrix([0, 0, 0]))
        else:
            matrix = get_matrix(vec_subtract(origin, parentOrigin))
        vertex_refs = []
        if actor.Geometry():
            vertex_refs = self.poser2egg[self.get_actor_index(actor)]
        child_joints = []
        for child in actor.Children():
            child_joint = self.collect_joints(child, level + 1)
            if child_joint is not None:
                child_joints += child_joint
        return [(actorName, matrix, child_joints, vertex_refs)]

    def get_actor_index(self, actor):
        for i, a in enumerate(self.uniActorList):
            if a.InternalName() == actor.InternalName():
                return i
        return None

    def write(self):
        lines = []
        lines += "<CoordinateSystem> { Y-Up-Right }\n"
        lines += write_comment('poser2egg - ' + self.figure_name, 0)
        # write materials and textures
        print 'Writing Materials ...'
        for material in self.materials.values():
            lines += material.write()
        if self.options["textures"] == True:
            for texture in self.textures.values():
                lines += texture.write()
        # write figure
        print 'Writing Rig ...'
        lines += "<Group> %s {\n  <Dart> { 1 }\n" % (self.figure_name, )
        # write joints
        lines += self.write_joints(self.joints)
        poser.Scene().ProcessSomeEvents()
        # write vertex pool
        lines += self.write_vertex_pool()
        poser.Scene().ProcessSomeEvents()
        # write polygons
        lines += self.write_polygons()
        poser.Scene().ProcessSomeEvents()
        lines += '} // End Group: %s \n' % (self.figure_name, )
        return lines

    def collect_materials(self, figure):
        egg_materials = {}
        for material in figure.Materials():
            mat_name = material.Name()
            if mat_name == 'Preview':
                continue
            egg_materials[mat_name] = EggMaterial(material)
        return egg_materials, EggTexture.ALL_TEXTURES

    def write_joints(self, joint, indent=1):
        lines = []
        for (joint_name, joint_matrix, child_joints, vertex_refs) in joint:
            #print joint_name
            lines += indent_string('  <Joint> %s {\n' % joint_name, indent)
            lines += write_transform(joint_matrix, indent + 1)

            lines += indent_string('<VertexRef> {\n', indent + 1)
            vx = [str(v) for v in vertex_refs]
            lines.append(indent_string('%s\n' % (' '.join(vx)), indent + 2))
            lines.append(indent_string('<Ref> { mesh }\n', indent + 2))
            lines.append(indent_string('}\n', indent + 1))

            lines += self.write_joints(child_joints, indent + 1)
            lines += indent_string('  } // End joint %s \n' % joint_name, indent)

        return lines

    def write_vertex_pool_exp(self):
        uniGeometry, a, v = self.figure.UnimeshInfo()
        sum = 0
        for a0 in a:
            print a0.Name(), a0.Geometry().NumVertices()
            sum += a0.Geometry().NumVertices()
        print "Total " + str(sum)
        vertices, tex_vertices = uniGeometry.Vertices(), uniGeometry.TexVertices()
        sets = uniGeometry.Sets()
        tsets = uniGeometry.TexSets()
        print len(vertices), type(vertices)
        print len(tex_vertices)
        print len(uniGeometry.Sets()), type(sets)
        print len(uniGeometry.TexSets())
        print len(uniGeometry.Polygons())
        print len(uniGeometry.TexPolygons())
        #print sets
        uvs = {}
        poser.Scene().ProcessSomeEvents()
        sum = 0
        for k, p in enumerate(uniGeometry.Polygons()):
            #print "poly " +str(k)
            tp = uniGeometry.TexPolygons()[k]
            set = sets[p.Start(): p.Start() + p.NumVertices()]
            tset = tsets[tp.Start(): tp.Start() + tp.NumTexVertices()]
            sum += len(set)
            for k2, v in enumerate(set):
                #print v
                if v not in uvs:
                    uvs[v] = tex_vertices[tset[k2]]
        print len(uvs)
        print sum
        print "Check on counts"
        missed = 0
        poser.Scene().ProcessSomeEvents()
        #for i in range(0, uniGeometry.NumVertices() ):         
        #    try:
        #       sets.index(i)
        #    except:
        #       missed+=1
        #print "Lost vertices ", missed

        
        numVertices = uniGeometry.NumVertices() 
        normals = uniGeometry.Normals() 
        texVertices=uniGeometry.TexVertices()
        percentComplete = 0 
        print 'Writing vertices ...'
        lines = []
        lines += '  <VertexPool> mesh {\n'
        self.unknown=[]
        for i in range(0, numVertices): 
            p = int((i / float(numVertices)) * 100) 
            if not p == percentComplete: 
               print '*', 
               if p % 10 == 0: 
                   print p, '%' 
                   poser.Scene().ProcessSomeEvents()
               percentComplete = p 
            v = vertices[i] 
            n = normals[i]
            try:
               kx=sets.index(i)
               t=tex_vertices[tsets[kx]]
               lines.append('    <Vertex> %s { %f %f %f <Normal> { %f %f %f } <UV> { %f %f } <RGBA> { 0 1 0 0.9} }\n' %
                         (str(i), v.X(), v.Y(), v.Z(),
                          n.X() != 'nan' or 0, n.Y() != 'nan' or 0, n.Z() != 'nan' or 0,
                          t.U(), t.V()))
            except ValueError:
	       self.unknown.append(i)
               lines.append('    <Vertex> %s { %f %f %f <Normal> { %f %f %f } <RGBA> { 1 0 0 1} }\n' %
                         (str(i), v.X(), v.Y(), v.Z(),
                          n.X() != 'nan' or 0, n.Y() != 'nan' or 0, n.Z() != 'nan' or 0))

        lines += '  } // End VertexPool: mesh\n'
        print '* 100 %'
        return lines

    def write_vertex_pool(self):
        print 'Writing vertices ...'
        lines = []
        lines += '  <VertexPool> mesh {\n'
        for (i, v_tuple, n, t) in self.vertices:
            lines.append('    <Vertex> %s { %f %f %f <Normal> { %f %f %f } <UV> { %f %f } }\n' %
                         (str(i), v_tuple[0], v_tuple[1], v_tuple[2],
                          n.X() != 'nan' or 0, n.Y() != 'nan' or 0, n.Z() != 'nan' or 0,
                          t.U(), t.V()))

        lines += '  } // End VertexPool: mesh\n'
        print '* 100 %'
        return lines

    def write_polygons_exp(self):
        uniGeometry,a,v=self.figure.UnimeshInfo()
        polygons = uniGeometry.Polygons() 
        numPolygons = uniGeometry.NumPolygons() 
        sets = uniGeometry.Sets() 

        lines = []
        print 'Writing Polygons ...'
        percentComplete = 0 
        for i in range(0, numPolygons): 
          polygon = polygons[i] 
          start = polygon.Start() 
          refs = ' '.join([str(j) for j in sets[start : start + polygon.NumVertices()]]) 
          polygon_trefs = ' '.join(
               "<TRef> {%s}" % texture_name for texture_name in self.materials[polygon.MaterialName()].textures)	
          #polygon_trefs=""
          lines.append(
               "  <Polygon> {\n    %s\n    \n    <VertexRef> { %s <Ref> { mesh } } \n}\n" % (
                  polygon_trefs, refs, ))

        lines.append(
             "  <Polygon> {\n    \n    <VertexRef> { %s <Ref> { mesh } } \n}\n" % (
             ' '.join([str(x) for x in self.unknown]) ))
        return lines

    def write_polygons(self):
        lines = []
        print 'Writing Polygons ...'
        for (group_name, group_polys) in self.polygons:
            lines += "<Group> %s {\n" % (group_name, )
            for (polygon, start_index, num_vertices) in group_polys:
                refs = ' '.join([str(j) for j in range(start_index, start_index + num_vertices)])
                if self.options["textures"] == True:
                    polygon_trefs = ' '.join(
                        "<TRef> {%s}" % texture_name for texture_name in self.materials[polygon.MaterialName()].textures)
                else:
                    polygon_trefs = ""
                lines.append(
                    "  <Polygon> {\n    %s\n    <MRef> { %s } \n    <VertexRef> { %s <Ref> { mesh } } \n}\n" % (
                        polygon_trefs, polygon.MaterialName(), refs, ))
            lines += "\n}\n"
        print '* 100 %'
        return lines

    def collect_vertices(self, uniActorList):
        bake_morph = self.options["morph"] == self.BAKE_MORPHS
        print 'Collecting vertices ...'
        egg_vertices = []
        egg_polygons = []
        poser2egg = {}
        self.egg_uvs = {}
        # egg vertex index is different from poser
        vertex_index = 0
        for actor in uniActorList:
            print actor.Name()
            actor_index = self.get_actor_index(actor)
            poser2egg[actor_index] = {}
            # get actor geom data
            geom = actor.Geometry()
            # check morph options
            if bake_morph:
                all_params = actor.Parameters()
                # get morph targets
                #morphs = [p for p in all_params if not p.Name().startswith('EMPTY') and not p.Name().startswith('V4') and p.Name() != '-' and p.IsMorphTarget() and (abs(p.Value()-0.0) > 0.001) and p.Hidden() != 1]
                morphs = [p for p in all_params if p.IsMorphTarget() and not p.Name().startswith('EMPTY') and p.Name() != '-' and not p.Name().startswith('V4') and (abs(p.Value() - 0.0) > 0.1)]
                #morphs = [p for p in all_params if p.IsMorphTarget() and p.IsValueParameter() and (abs(p.Value() - 0.0) > 0.1)]
                # poser vertices/texture data
            vertices, tex_vertices, normals = geom.Vertices(), geom.TexVertices(), geom.Normals()
            # poser polygon/texture data (index to start in sets/tex_sets + number of vertices)
            polygons, tex_polygons = geom.Polygons(), geom.TexPolygons()
            # poser sets/texture sets containing vertices id for vertices/tex_vertices arrays
            sets, tex_sets = geom.Sets(), geom.TexSets()
            # collect all geom data for current actor and present as egg group
            group_name = fix_name(actor.Name())
            group_polygons = []
            for polygon_index, polygon in enumerate(polygons):
                poly_start = vertex_index
                start = polygon.Start()
                # get tex_polygon and tex_set for current polygon
                tex_polygon = tex_polygons[polygon_index]
                tex_set = tex_sets[tex_polygon.Start(): tex_polygon.Start() + tex_polygon.NumTexVertices()]
                # get all polygon vertices
                for k, v in enumerate(sets[start: start + polygon.NumVertices()]):
                    vertex = vertices[v]
                    self.egg_uvs[start + k] = tex_vertices[tex_set[k]]
                    x, y, z = vertex.X(), vertex.Y(), vertex.Z()
                    if bake_morph:
                        for morph in morphs:
                            dx, dy, dz = morph.MorphTargetDelta(v)
                            x += dx * morph.Value()
                            y += dy * morph.Value()
                            z += dz * morph.Value()
                    egg_vertices.append((vertex_index, (x, y, z), normals[v], tex_vertices[tex_set[k]]))
                    poser2egg[actor_index][vertex_index] = vertex_index
                    # increment egg vertex index
                    vertex_index += 1
                    # add egg polygon data to group polygons (poser polygon + start/length in egg_vertices list)
                group_polygons.append((polygon, poly_start, vertex_index - poly_start))
            egg_polygons.append((group_name, group_polygons))
            poser.Scene().ProcessSomeEvents()
        return egg_vertices, egg_polygons, poser2egg


class Poser2Egg():
    SKIP_OVERWRITE = True
    RECOMPUTE_NORMALS = False

    def export(self):
        # get selected figure
        figure = poser.Scene().CurrentFigure()
        #figure = poser.Scene().CurrentActor()
        body_part = False
        assert figure, 'No currently selected figure!'
        figureName = fix_name(figure.Name())
        abort = False
        getSaveFile = poser.DialogFileChooser(2, 0, "Save Egg File", figureName, '', '*.egg')
        getSaveFile.Show()
        fileName = getSaveFile.Path()
        if os.path.exists(fileName) and not Poser2Egg.SKIP_OVERWRITE:
            if not poser.DialogSimple.YesNo("Overwrite " + fileName + "?"):
                abort = True
        if not abort:
            if body_part:
                ikStatusList = self.remove_ik_chains(figure)
            print 'Exporting character:', figureName, 'to', fileName
            try:
                egg_obj = EggObject(figure)
                lines = egg_obj.export()
                #print lines
                output = open(fileName, 'w')
                output.write("".join(lines))
                output.close()
            except IOError, (errno, strerror):
                print 'failed to open file', fileName, 'for writing'
                print "I/O error(%s): %s" % (errno, strerror)
            else:
                print 'finished writing data'
            if body_part:
                self.restore_ik_chains(figure, ikStatusList)
            if Poser2Egg.RECOMPUTE_NORMALS:
                self.recompute_egg_normals(fileName)

    def optimize_egg(self, fileName):
        print 'processing egg file with panda binaries...'
        os.chdir(OUTPUT_PATH)
        cmdln = 'echo Optimizing egg character ... && ' +\
                'egg-optchar "' + fileName + '" -inplace -keepall -TS 12 && ' +\
                'echo ""&& ' +\
                'echo Converting to bam file ... && ' +\
                'egg2bam "' + fileName + '" -o "' + fileName + '.bam" && ' +\
                'echo Opening pview ... && ' +\
                'start pview "' + fileName + '.bam" -c -l'
        if os.system(cmdln) == 1:
            print "Error while processing egg file!"

    def recompute_egg_normals(self, fileName):
        print "Recompute vertex normals"
        os.chdir(os.path.dirname(fileName))
        cmdln = 'egg-trans "' + fileName + '" -nv 120 -o ' + fileName
        print cmdln
        if os.system(cmdln) == 1:
            print "Error while processing egg file!"

    def remove_ik_chains(self, figure):
        ikStatusList = []
        for i in range(0, figure.NumIkChains()):
            ikStatusList.append(figure.IkStatus(i))
            figure.SetIkStatus(i, 0)  # Turn off
        return ikStatusList

    def restore_ik_chains(self, figure, ikStatusList):
        for i in range(0, figure.NumIkChains()):
            figure.SetIkStatus(i, ikStatusList[i])


exporter = Poser2Egg()
exporter.export()
