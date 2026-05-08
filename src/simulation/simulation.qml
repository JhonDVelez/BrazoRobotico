import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick3D
import QtQuick3D.Helpers
import "."

View3D {
    id: view3D
    anchors.fill: parent

    // Properties exposed for Python
    property alias trackedPosition: trackedNode.scenePosition
    property real effectorY: robot.endEffector.scenePosition.y
    property real effectorX: robot.endEffector.scenePosition.x
    property real effectorZ: robot.endEffector.scenePosition.z
    property real sceneEffectorX: -effectorX
    property real sceneEffectorY: effectorY - 100
    property real sceneEffectorZ: effectorZ
    property url boardTexture: "maps/boardTexture.png"
    property url floorTexture: "maps/floorTexture.png"
    property real x_offset: -100
    property alias bgColor: env.clearColor
    property alias bgMode: env.backgroundMode
    property alias floorColor: floorMaterial.baseColor
    property alias sphereOrangePos: sphereOrange.modelPosition
    property alias sphereGreenPos: sphereGreen.modelPosition
    property alias sphereBluePos: sphereBlue.modelPosition
    property alias spherePurplePos: spherePurple.modelPosition
    property alias sphereYellowPos: sphereYellow.modelPosition

    environment: SceneEnvironment {
        id: env
        clearColor: "#191B20"
        backgroundMode: SceneEnvironment.Color
        antialiasingMode: SceneEnvironment.MSAA
        antialiasingQuality: SceneEnvironment.High
        InfiniteGrid { 
            gridInterval: 10
        }
    }

    DirectionalLight {
        eulerRotation.x: -35
        eulerRotation.y: -45
        castsShadow: true
        shadowMapQuality: Light.ShadowMapQualityVeryHigh
        shadowFactor: 30
        brightness: 1
    }

    Model {
        id: cameraOrigin
        position.x: -150
        position.y: 300
        eulerRotation.y: -135
        eulerRotation.x: -20

        PerspectiveCamera {
            id: cameraNode
            clipNear: 1
            clipFar: 30000
            z: 1300
            fieldOfView: 30
        }
    }

    OrbitCameraController {
        camera: cameraNode
        origin: cameraOrigin
    }

    Openbotv_v1 {
        id: robot
        scale: Qt.vector3d(1000, 1000, 1000)
        position: Qt.vector3d(0, 90, 0)
    }

    Box {
        id: box3D
        scale: Qt.vector3d(1000, 1000, 1000)
        eulerRotation.y: 180
        eulerRotation.z: 180
        position: Qt.vector3d(view3D.x_offset+15, 105, 15)
    }

    Model {
        id: floor
        source: "meshes/floor.mesh"
        scale: Qt.vector3d(4000, 1, 4000)

        materials: [
            PrincipledMaterial {
                id: floorMaterial
                baseColor: "black"        // ← alias floorColor controla el color
                alphaMode: PrincipledMaterial.Blend
                opacityMap: Texture {
                    source: view3D.floorTexture   // solo actúa como máscara alpha
                }
                roughness: 0.5
                indexOfRefraction: 1.45
            }
        ]
        receivesShadows: true
    }

    Model {
        id: tablero
        
        // Define X by Y dimensions
        geometry: PlaneGeometry {
            plane: PlaneGeometry.XZ
            width: 369.57
            height: 159.766
        }
        scale: Qt.vector3d(1, 1, 1)
        position: Qt.vector3d(view3D.x_offset-85, 100, 0)
        eulerRotation.y: -90

        materials: [
            PrincipledMaterial {
                baseColorMap: Texture {
                    generateMipmaps: true
                    mipFilter: Texture.Linear
                    magFilter: Texture.Linear
                    source: view3D.boardTexture
                }
                roughness: 0.5
                indexOfRefraction: 1.45
                cullMode: PrincipledMaterial.NoCulling
                alphaMode: PrincipledMaterial.Opaque
            }
        ]
        receivesShadows: true   
    }

    Sphere {
        id: sphereOrange
        modelColor: "#d3612d"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    Sphere {
        id: sphereGreen
        modelColor: "#44ff44"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    Sphere {
        id: sphereBlue
        modelColor: "#4488ff"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    Sphere {
        id: sphereYellow
        modelColor: "#c3f314"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    Sphere {
        id: spherePurple
        modelColor: "#a11e90"
        modelPosition: Qt.vector3d(0, 0, 0)
    }

    // "Ghost" node that follows the object you want to track
    Node {
        id: trackedNode
        position: robot.endEffector ? robot.endEffector.scenePosition : Qt.vector3d(0, 0, 0)
    }

    // Overlay XYZ en esquina superior derecha
    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 10
        width: 160
        height: 80
        color: "#aa000000"
        radius: 6

        Column {
            anchors.centerIn: parent
            spacing: 4

            Label {
                color: "#ff4444"
                font.bold: true
                text: "X: " + sceneEffectorX.toFixed(4)
            }
            Label {
                color: "#4488ff"
                font.bold: true
                text: "Y: " + sceneEffectorZ.toFixed(4)
            }
            Label {
                color: "#44ff44"
                font.bold: true
                text: "Z: " + sceneEffectorY.toFixed(4)
            }
        }
    }

    Model {
        id: projectionCylinder

        source: "#Cylinder"

        position: Qt.vector3d(
            effectorX,
            effectorY / 2.0,   // center between Y=0 and endEffector.y
            effectorZ
        )

        scale: Qt.vector3d(
            0.04,                       // fine radius in X
            effectorY / 100,            
            0.04                        // fine radius in Z
        )

        materials: [
            PrincipledMaterial {
                baseColor: "#44ff44"
                roughness: 0.3
                metalness: 0.1
            }
        ]
    }

    Button {
        icon.source: "../gui/icons/home.png"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 10
        onClicked: {
            cameraOrigin.position = Qt.vector3d(-150, 300, 0)
            cameraOrigin.eulerRotation = Qt.vector3d(-20, -135, 0)
            cameraNode.z = 1300
        }
    }
}