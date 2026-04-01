import QtQuick
import QtQuick.Controls
import QtQuick3D
import QtQuick3D.Helpers
import "."

View3D {
    id: view3D
    anchors.fill: parent

    // Propiedades expuestas para Python
    property alias trackedPosition: trackedNode.scenePosition
    property real effectorY: robot.endEffector.scenePosition.y
    property real effectorX: robot.endEffector.scenePosition.x
    property real effectorZ: robot.endEffector.scenePosition.z
    property real sceneEffectorX: -effectorX * 1000
    property real sceneEffectorY: effectorY * 1000
    property real sceneEffectorZ: effectorZ * 1000

    environment: ExtendedSceneEnvironment {
        backgroundMode: SceneEnvironment.SkyBox
        lightProbe: Texture {
            textureData: ProceduralSkyTextureData {
                textureQuality: ProceduralSkyTextureData.SkyTextureQualityHigh
                groundHorizonColor: "lightgray"
                groundCurve: 0.2
            }
        }
        InfiniteGrid { 
            gridInterval: 0.01
        }
        tonemapMode: SceneEnvironment.TonemapModeAces
        antialiasingMode: SceneEnvironment.MSAA
        antialiasingQuality: SceneEnvironment.VeryHigh
    }

    DirectionalLight {
        visible: true
        eulerRotation.x: -45
        eulerRotation.y: 45
    }

    Node {
        id: originNode
        position: Qt.vector3d(0, 0.25, 0)
        eulerRotation: Qt.vector3d(-20, 135, 0)
        PerspectiveCamera {
            id: cameraNode
            position: Qt.vector3d(0.1, 0, 1.3)
            clipFar: 10
            clipNear: 0.05
            fieldOfView: 30
        }
    }

    OrbitCameraController {
        anchors.fill: parent
        origin: originNode
        camera: cameraNode
    }

    Openbotv_v1 {
        id: robot
        scale: Qt.vector3d(1, 1, 1)
    }

    // Nodo "fantasma" que sigue al objeto que quieres trackear
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

        source: "#Cylinder"  // primitiva built-in

        position: Qt.vector3d(
            effectorX,
            effectorY / 2.0,   // centro entre Y=0 y endEffector.y
            effectorZ
        )

        scale: Qt.vector3d(
            0.00004,                       // radio fino en X
            effectorY / 100,            // QtQuick3D #Cylinder tiene height=2 por defecto
            0.00004                        // radio fino en Z
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
            position: 
            originNode.position = Qt.vector3d(0, 0.25, 0)
            originNode.eulerRotation = Qt.vector3d(-20, 135, 0)
            cameraNode.position = Qt.vector3d(0.1, 0, 1.3)
        }
    }
}