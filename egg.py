# -*- coding: utf-8 -*-

from utils import *
from euclid import Quaternion

#supported poser texture modes
class TextureMode:
    MODULATE = 'MODULATE'
    NORMAL = 'NORMAL'
    GLOSS = 'GLOSS'
    ALPHA = 'ALPHA'


# Class for egg presentation of Poser material
class EggMaterial:
    def __init__(self, poser_material):
        self.poser_material = poser_material
        self.name = egg_safe_same(poser_material.Name())

        textures = [self._check_texture(poser_material.TextureMapFileName(), '_texture', TextureMode.MODULATE),
                   self._check_texture(poser_material.BumpMapFileName(), '_bump', TextureMode.NORMAL),
                   self._check_texture(poser_material.TransparencyMapFileName(), '_transparency', TextureMode.ALPHA)]
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


# Class for egg presentation of Poser material textures
class EggTexture:
    EMPTY_TEXTURE = poser.ContentRootLocation().replace("\\", '/').replace(":", "")
    ALL_TEXTURES = {}

    def __init__(self, filename, texture_name, texture_mode):
        self.texture_mode = texture_mode
        self.filename = None
        if filename is not None:
            self.filename = filename.replace("\\", '/').replace(":", "")
        self.name = egg_safe_same(texture_name)

    def check_texture(self):
        if self.filename != EggTexture.EMPTY_TEXTURE and self.filename is not None:
            if self.filename not in EggTexture.ALL_TEXTURES:
                EggTexture.ALL_TEXTURES[self.filename] = self
            return EggTexture.ALL_TEXTURES[self.filename].name
        return None

    def write(self):
        lines = ["<Texture> %s {\n \"%s\" \n" % (self.name, self.filename)]
        # poser transparency textures are separate file and exported as pure alpha in egg
        if self.texture_mode == TextureMode.ALPHA:
            lines += "   <Scalar> format { alpha }\n"
            lines += "   <Scalar> envtype { %s }" % TextureMode.MODULATE
        else:
            lines += "   <Scalar> envtype { %s }" % self.texture_mode
        lines += "   <Scalar> wrap { %s }" % 'REPEAT'
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

    def write(self):
        lines = []
        lines += "<CoordinateSystem> { Y-Up-Right }\n"
        lines += write_comment('poser2egg - ' + self.figure_name, 0)
        # write materials and textures
        print 'Writing Materials ...'
        lines + self.write_materials()
        # write rig
        print 'Writing Rig ...'
        lines += "<Group> %s {\n  <Dart> { 1 }\n" % (self.figure_name, )
        # write joints
        lines += self.write_joints(self.joints)
        poser.Scene().ProcessSomeEvents()
        # write vertex pool
        print 'Writing vertices ...'
        lines += self.write_vertex_pool()
        poser.Scene().ProcessSomeEvents()
        # write polygons
        print 'Writing Polygons ...'
        lines += self.write_polygons()
        poser.Scene().ProcessSomeEvents()
        lines += '} // End Group: %s \n' % (self.figure_name, )
        return lines

    def collect_joints(self, actor, level):
        if not actor.IsBodyPart() or actor.Name() == 'BodyMorphs':
            return
        actorName = fix_name(actor.Name())
        print indent_string('processing %s' % actorName, level)
        #origin = actor.Origin()
        #parentOrigin = actor.Parent().Origin()
        if actor.Name() == self.figure.ParentActor().Name():
            #matrix = get_matrix(origin)
            matrix = actor.WorldMatrix()  # get_matrix(origin)
        else:
            #matrix = get_matrix(vec_subtract(origin, parentOrigin))
            matrix = actor.LocalMatrix()
        vertex_refs = []
        if actor.Geometry():
            vertex_refs = self.poser2egg[self.get_actor_index(actor)]
        child_joints = []
        for child in actor.Children():
            child_joint = self.collect_joints(child, level + 1)
            if child_joint is not None:
                child_joints += child_joint
        return [(actorName, matrix, child_joints, vertex_refs, actor)]

    def write_joints(self, joint, indent=1):
        lines = []
        for (joint_name, joint_matrix, child_joints, vertex_refs, actor) in joint:
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

    def get_actor_index(self, actor):
        for i, a in enumerate(self.uniActorList):
            if a.InternalName() == actor.InternalName():
                return i
        return None

    def collect_materials(self, figure):
        egg_materials = {}
        for material in figure.Materials():
            mat_name = material.Name()
            if mat_name == 'Preview':
                continue
            egg_materials[mat_name] = EggMaterial(material)
        return egg_materials, EggTexture.ALL_TEXTURES

    def write_materials(self):
        lines = []
        for material in self.materials.values():
            lines += material.write()
        if self.options["textures"] == True:
            for texture in self.textures.values():
                lines += texture.write()
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

    def write_vertex_pool(self):
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

    def write_polygons(self):
        lines = []
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

    def collect_anims(self):
        anims_data = {}
        for frame in xrange(0, poser.Scene().NumFrames() - 1):
        #for frame in xrange(0, 3):
            poser.Scene().SetFrame(frame)
            poser.Scene().DrawAll()
            self.collect_anims2(self.joints, anims_data)
        return anims_data

    def collect_anims2(self, joint, anims):
        for (joint_name, joint_matrix, child_joints, vertex_refs, actor) in joint:
            #print "anims for %s" % joint_name
            #get bone displacement
            displacement = actor.LocalDisplacement()
            origin = actor.Origin()
            parentOrigin = actor.Parent().Origin()
            if actor.Name() == self.figure.ParentActor().Name():
                parentOrigin = origin
            displacement = vec_add(vec_subtract(origin, parentOrigin), displacement)
            displacement = vec_subtract(origin, parentOrigin)
            # get rotation
            quat_tuple = actor.LocalQuaternion()
            quat = Quaternion(quat_tuple[0], quat_tuple[1], quat_tuple[2], quat_tuple[3])
            hpr = radians_to_degrees(quat.get_euler())
            #store displacement/rotation in anims data
            if joint_name not in anims:
                anims[joint_name] = []
            anims[joint_name].append((displacement, hpr))
            self.collect_anims2(child_joints, anims)
        return anims

    def write_animation(self):
        print 'Writing animation ...'
        anims_data = self.collect_anims()
        #print anims_data
        #return
        lines = []
        lines += '<Table> {\n'
        lines += indent_string('<Bundle> %s {\n' % self.figure_name, 1)
        lines += indent_string('<Table> "<skeleton>" {\n', 2)
        lines += self.write_animation_table(self.joints, anims_data, 3)
        lines += indent_string('}\n', 2)
        lines += indent_string('}\n', 1)
        lines += '}'

        return lines

    def write_animation_table(self, joint, anims_data, indent=1):
        lines = []
        for (joint_name, joint_matrix, child_joints, vertex_refs, actor) in joint:
            #print joint_name
            lines += indent_string('<Table> %s {\n' % joint_name, indent)
            lines += indent_string('<Xfm$Anim> xform {\n', indent + 1)
            lines += indent_string('<Scalar> order { sprht }\n', indent + 2)
            lines += indent_string('<Scalar> contents { prhxyz }\n', indent + 2)
            #lines += indent_string('<Scalar> contents { ijkprhxyz }\n', indent + 2)
            lines += indent_string('<Scalar> fps { %u }\n' % 2, indent + 2)
            lines += indent_string('<V> {\n', indent + 2)
            for frame in xrange(0, poser.Scene().NumFrames() - 1):
                displacement, hpr = anims_data[joint_name][frame]
                #lines += indent_string("%s %s %s %s %s %s %s %s %s\n" %
                lines += indent_string("%s %s %s %s %s %s\n" %
                        (
                            hpr[2], hpr[1], hpr[0],
                            displacement[0], displacement[1], displacement[2]
                        ),
                    indent + 3)
            lines += indent_string('}\n', indent + 2)
            lines += indent_string('}\n', indent + 1)
            lines += self.write_animation_table(child_joints, anims_data, indent + 2)
            lines += indent_string('} // End table %s \n' % joint_name, indent)

        return lines
