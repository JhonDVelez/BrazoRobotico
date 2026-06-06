import QtQuick
import QtQuick3D

Node {
    id: root

    property color modelColor: "white"
    property vector3d modelPosition: Qt.vector3d(0, 0, 0)
    property vector3d modelRotation: Qt.vector3d(0, 0, 0)
    property string meshSource: "meshes/sphere.mesh"

    // Oculto automáticamente si la posición es 0,0,0
    property bool hideOnZero: true

    visible: hideOnZero
             ? !(modelPosition.x === 0 && modelPosition.y === 0 && modelPosition.z === 0)
             : true
    Node {
        position: root.modelPosition
        eulerRotation: root.modelRotation
        Model {
            source: root.meshSource
            scale: Qt.vector3d(1, 1, 1)
            eulerRotation: Qt.vector3d(-90, 0, 0)

            materials: [
                PrincipledMaterial {
                    baseColor: root.modelColor
                    roughness: 0.4
                }
            ]
            receivesShadows: true
        }
    }
}