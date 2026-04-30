import QtQuick
import QtQuick.Controls
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
    property real sceneEffectorX: -effectorX * 1000
    property real sceneEffectorY: effectorY * 1000
    property real sceneEffectorZ: effectorZ * 1000
    property url boardTexture: "maps/boardTexture.png"
    property real x_offset: -0.1

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
        temporalAAEnabled: true
        antialiasingQuality: SceneEnvironment.VeryHigh
    }

    DirectionalLight {
        id: sun
        castsShadow: true
        shadowFactor: 100
        shadowMapQuality: DirectionalLight.ShadowMapQualityHigh
        brightness: 1.0
        visible: true
        eulerRotation.x: -45
        eulerRotation.y: 45                   
    }

    Node {
        id: cameraOrigin
        position.x: -0.15
        position.y: 0.3
        eulerRotation.y: -135
        eulerRotation.x: -20

        PerspectiveCamera {
            id: cameraNode
            clipNear: 0.001
            clipFar: 3.0
            z: 1.3
            fieldOfView: 30
        }
    }

    OrbitCameraController {
        camera: cameraNode
        origin: cameraOrigin
    }

    Openbotv_v1 {
        id: robot
        scale: Qt.vector3d(1, 1, 1)
        position: Qt.vector3d(0, 0.09, 0)
    }

    Box {
        id: box3D
        scale: Qt.vector3d(1, 1, 1)
        eulerRotation.y: 180
        eulerRotation.z: 180
        position: Qt.vector3d(view3D.x_offset+0.015, 0.105, 0.015)
    }

    Model {
        id: tablero
        
        // Define X by Y dimensions
        geometry: PlaneGeometry {
            plane: PlaneGeometry.XZ
            width: 0.36957
            height: 0.159766
        }
        scale: Qt.vector3d(1, 1, 1)
        position: Qt.vector3d(view3D.x_offset-0.085, 0.1, 0)
        eulerRotation.y: -90

        materials: [
            PrincipledMaterial {
                baseColorMap: Texture {
                    generateMipmaps: true
                    mipFilter: Texture.Linear
                    source: view3D.boardTexture
                }
                roughness: 0.5
                indexOfRefraction: 1.45
                cullMode: PrincipledMaterial.NoCulling
                alphaMode: PrincipledMaterial.Opaque
            }
        ]
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
            0.00004,                       // fine radius in X
            effectorY / 100,            
            0.00004                        // fine radius in Z
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
            cameraOrigin.position = Qt.vector3d(-0.15, 0.3, 0)
            cameraOrigin.eulerRotation = Qt.vector3d(-20, -135, 0)
            cameraNode.z = 1.3
        }
    }
}