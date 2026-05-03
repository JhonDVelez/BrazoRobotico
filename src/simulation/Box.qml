import QtQuick
import QtQuick3D

Node {
    id: box

    // Resources
    property url textureData: "maps/BoxTextureDataC.png"
    property url textureData7: "maps/BoxTextureDataR.png"
    Texture {
        id: _0_texture
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: box.textureData
    }
    Texture {
        id: node0
        generateMipmaps: true
        mipFilter: Texture.Linear
        source: box.textureData7
    }
    PrincipledMaterial {
        id: bake_material3
        objectName: "Bake"
        baseColorMap: _0_texture
        metalnessMap: node0
        roughnessMap: node0
        roughness: 1
        cullMode: PrincipledMaterial.NoCulling
        alphaMode: PrincipledMaterial.Opaque
    }

    // Nodes:
    Model {
        id: _MergedNode_02
        objectName: "Bake"
        position.x: 0.00358239
        position.y: 0.0536806
        position.z: 0.00699591
        rotation.x: -4.37114e-08
        rotation.y: 0
        rotation.z: 1
        rotation.scalar: 0
        scale.x: 0.001
        scale.y: 0.001
        scale.z: 0.001
        source: "meshes/caja_mesh.mesh"
        materials: [
            bake_material3
        ]
        castsShadows: true
        receivesShadows: true   
    }
}
