import QtQuick
import QtQuick3D

Node {
    id: _3_texture19

    // Resources
    property url textureData16: "maps/textureData16.png"
    property url textureData12: "maps/textureData12.png"
    property url textureData17: "maps/textureData17.png"
    property url textureData22: "maps/textureData22.png"
    property url textureData11: "maps/textureData11.png"
    property url textureData33: "maps/textureData33.png"
    property url textureData38: "maps/textureData38.png"
    Texture {
        id: _6_texture6
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: _3_texture19.textureData16
    }
    Texture {
        id: _5_texture11
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: _3_texture19.textureData12
    }
    Texture {
        id: _4_texture15
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: _3_texture19.textureData17
    }
    Texture {
        id: _3_texture21
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: _3_texture19.textureData22
    }
    Texture {
        id: _2_texture24
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: _3_texture19.textureData11
    }
    Texture {
        id: _1_texture31
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: _3_texture19.textureData33
    }
    Texture {
        id: _0_texture36
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: _3_texture19.textureData38
    }
    PrincipledMaterial {
        id: material_005_material4
        objectName: "Material.005"
        baseColorMap: _6_texture6
        roughness: 0.5
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_001_material10
        objectName: "Material.001"
        baseColorMap: _5_texture11
        roughness: 0.5
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: _6_texture4
        objectName: "Material.002"
        baseColorMap: _4_texture15
        roughness: 0.5
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_003_material20
        objectName: "Material.003"
        baseColorMap: _3_texture21
        roughness: 0.5
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_004_material24
        objectName: "Material.004"
        baseColorMap: _2_texture24
        roughness: 0.5
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_007_material30
        objectName: "Material.007"
        baseColorMap: _1_texture31
        roughness: 0.5
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_006_material35
        objectName: "Material.006"
        baseColorMap: _0_texture36
        roughness: 0.5
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_008_material40
        objectName: "Material.008"
        baseColor: "#66ffffff"
        baseColorMap: _6_texture6
        roughness: 0.5
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Blend
    }

    // Nodes:
    Model {
        id: base_link_mesh3
        objectName: "base_link"
        scale: Qt.vector3d(0.001, 0.001, 0.001)
        source: "meshes/base_link_mesh4.mesh"
        materials: [
            material_005_material4
        ]
        Model {
            id: arm1_link_18
            objectName: "arm1_link_1"
            position: Qt.vector3d(0.0213967, 122.693, 1.2751)
            source: "meshes/arm1_link_1_mesh8.mesh"
            materials: [
                material_001_material10
            ]
            Model {
                id: arm2_link_112
                objectName: "arm2_link_1"
                position: Qt.vector3d(-0.0400905, 32.5683, 1.2449)
                source: "meshes/clamp_arm_link_1_mesh27.mesh"
                materials: [
                    _6_texture4
                ]
                Model {
                    id: arm3_link_117
                    objectName: "arm3_link_1"
                    position: Qt.vector3d(-0.13914, 93.4278, 0.583994)
                    source: "meshes/arm3_link_1_mesh19.mesh"
                    materials: [
                        material_003_material20
                    ]
                    Model {
                        id: arm4_link_1_mesh22
                        objectName: "arm4_link_1"
                        position: Qt.vector3d(1.97872, 82.5878, -3.04708)
                        source: "meshes/arm4_link_1_mesh23.mesh"
                        materials: [
                            material_004_material24
                        ]
                        Model {
                            id: clamp_arm_link_127
                            objectName: "clamp_arm_link_1"
                            position: Qt.vector3d(1.51373, 29.5679, -0.888374)
                            source: "meshes/clamp_arm_link_1_mesh29.mesh"
                            materials: [
                                material_007_material30
                            ]
                            Model {
                                id: clamp2_link_133
                                objectName: "clamp2_link_1"
                                position: Qt.vector3d(18.0772, 70.2332, -0.108659)
                                scale: Qt.vector3d(1000, 1000, 1000)
                                source: "meshes/clamp2_link_1_mesh34.mesh"
                                materials: [
                                    material_006_material35
                                ]
                            }
                        }
                    }
                }
            }
        }
        Model {
            id: base_link_00138
            objectName: "base_link.001"
            source: "meshes/base_link_001_mesh39.mesh"
            materials: [
                material_008_material40
            ]
        }
    }

    // Animations:
}
