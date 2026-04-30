import QtQuick
import QtQuick3D

Node {
    id: node

    // Resources
    property url textureData: "maps/textureData.png"
    property url textureData10: "maps/textureData10.png"
    property url textureData15: "maps/textureData15.png"
    property url textureData20: "maps/textureData20.png"
    property url textureData25: "maps/textureData25.png"
    property url textureData30: "maps/textureData30.png"
    property url textureData35: "maps/textureData35.png"

    Texture {
        id: _6_texture
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: node.textureData
    }
    Texture {
        id: _5_texture
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: node.textureData10
    }
    Texture {
        id: _4_texture
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: node.textureData15
    }
    Texture {
        id: _3_texture
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: node.textureData20
    }
    Texture {
        id: _2_texture
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: node.textureData25
    }
    Texture {
        id: _1_texture
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: node.textureData30
    }
    Texture {
        id: _0_texture
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: node.textureData35
    }
    PrincipledMaterial {
        id: material_005_material
        objectName: "Material.005"
        baseColorMap: _6_texture
        roughness: 0.5          
        metalness: 0.0
        specularAmount: 0.3
        clearcoatAmount: 0.0    
        indexOfRefraction: 1.45
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_001_material
        objectName: "Material.001"
        baseColorMap: _5_texture
        roughness: 0.5
        metalness: 0.0
        specularAmount: 0.3
        clearcoatAmount: 0.0
        indexOfRefraction: 1.45
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_002_material
        objectName: "Material.002"
        baseColorMap: _4_texture
        roughness: 0.5
        metalness: 0.0
        specularAmount: 0.3
        clearcoatAmount: 0.0
        indexOfRefraction: 1.45
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_003_material
        objectName: "Material.003"
        baseColorMap: _3_texture
        roughness: 0.5
        metalness: 0.0
        specularAmount: 0.3
        clearcoatAmount: 0.0
        indexOfRefraction: 1.45
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_004_material
        objectName: "Material.004"
        baseColorMap: _2_texture
        roughness: 0.5
        metalness: 0.0
        specularAmount: 0.3
        clearcoatAmount: 0.0
        indexOfRefraction: 1.45
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_007_material
        objectName: "Material.007"
        baseColorMap: _1_texture
        roughness: 0.5
        metalness: 0.0
        specularAmount: 0.3
        clearcoatAmount: 0.0
        indexOfRefraction: 1.45
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_006_material
        objectName: "Material.006"
        roughness: 0.5
        metalness: 0.0
        specularAmount: 0.3
        clearcoatAmount: 0.0
        indexOfRefraction: 1.45
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }
    PrincipledMaterial {
        id: material_008_material
        objectName: "Material.008"
        baseColorMap: _6_texture
        roughness: 0.5
        metalness: 0.0
        specularAmount: 0.3
        clearcoatAmount: 0.0
        indexOfRefraction: 1.45
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }

    // Nodes:
    Model {
        id: base_link
        objectName: "base_link"
        scale: Qt.vector3d(0.001, 0.001, 0.001)
        source: "meshes/base_link_mesh.mesh"
        castsShadows: true
        receivesShadows: true
        materials: [
            material_005_material
        ]
        Model {
            id: arm1_link_1
            objectName: "arm1_link_1"
            position: Qt.vector3d(0.0213967, 122.693, 1.2751)
            source: "meshes/arm1_link_1_mesh.mesh"
            castsShadows: true
            receivesShadows: true   
            materials: [
                material_001_material
            ]
            Model {
                id: arm2_link_1
                objectName: "arm2_link_1"
                position: Qt.vector3d(-0.0400905, 32.5683, 3.8)
                source: "meshes/arm2_link_1_mesh.mesh"
                castsShadows: true
                receivesShadows: true
                materials: [
                    material_002_material
                ]
                Model {
                    id: arm3_link_1
                    objectName: "arm3_link_1"
                    position: Qt.vector3d(-0.13914, 93.4279, -2)
                    source: "meshes/arm3_link_1_mesh.mesh"
                    castsShadows: true
                    receivesShadows: true
                    materials: [
                        material_003_material
                    ]
                    Model {
                        id: arm4_link_1
                        objectName: "arm4_link_1"
                        position: Qt.vector3d(1.97872, 82.5878, -3.04708)
                        source: "meshes/arm4_link_1_mesh.mesh"
                        castsShadows: true
                        receivesShadows: true
                        materials: [
                            material_004_material
                        ]
                        Model {
                            id: clamp_arm_link_1
                            objectName: "clamp_arm_link_1"
                            position: Qt.vector3d(1.51373, 29.5679, 5)
                            source: "meshes/clamp_arm_link_1_mesh.mesh"
                            castsShadows: true
                            receivesShadows: true
                            materials: [
                                material_007_material
                            ]
                            Model {
                                id: clamp2_link_1
                                objectName: "clamp2_link_1"
                                position: Qt.vector3d(5.3, 73.0, -18.3)
                                source: "meshes/clamp2_link_1_mesh.mesh"
                                castsShadows: true
                                receivesShadows: true
                                materials: [
                                    material_006_material
                                ]
                            }
                            Node {
                                id: endEffectorTip
                                position: Qt.vector3d(10, 152.2, 0.83)

                                // Punto visible en la punta
                                Model {
                                    source: "#Sphere"
                                    scale: Qt.vector3d(0.07, 0.07, 0.07)  // compensando el 0.001 de base_link
                                    materials: [
                                        PrincipledMaterial {
                                            baseColor: "#44ff44"
                                            roughness: 0.2
                                            lighting: PrincipledMaterial.NoLighting
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }
        Model {
            id: base_link_001
            objectName: "base_link.001"
            source: "meshes/base_link_001_mesh.mesh"
            castsShadows: true
            receivesShadows: true
            materials: [
                material_008_material
            ]
        }
    }
    property alias endEffector: endEffectorTip 
}
