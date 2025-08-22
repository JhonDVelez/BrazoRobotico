import os
import numpy as np
from stl import mesh
import pyqtgraph.opengl as gl
from PyQt6.QtCore import QThread
from pyqtgraph.opengl import shaders
from pyqtgraph.opengl.shaders import ShaderProgram, VertexShader, FragmentShader


class OpenGLRobot(QThread):
    """ Clase que ejecuta la interfaz de openGl en un proceso diferente para pyqt para evitar 
        congelamientos en la interfaz

    Args:
        QThread (QThread): Define el proceso en que se ejecuta separado del principal 
    """

    def __init__(self, links):
        super().__init__()
        self.links = links
        self.gl_widget = gl.GLViewWidget()

        self.custom_shader()

        self.init_visualization()
        self.add_robot()

    def init_visualization(self):
        """Inicializar la visualización con PyQtGraph"""
        # Configurar la cámara
        self.gl_widget.setCameraPosition(distance=2, elevation=30, azimuth=45)
        self.gl_widget.setBackgroundColor([169, 165, 198])

        self.create_floor(size=100, tile_size=0.5)

    def create_floor(self, size=10, tile_size=1):
        """ Crea el suelo con un patron de tablero de ajedrez
        """

        vertices = []
        faces = []
        face_colors = []
        vertex_count = 0

        # Colores
        white_color = np.array([223/255, 223/255, 223/255, 1.0])
        blue_color = np.array([144/255, 170/255, 210/255, 1.0])

        for i in range(size):
            for j in range(size):
                # Determinar color
                if not (i + j) % 2:
                    color = white_color
                else:
                    color = blue_color

                # Posición del cuadrado
                x_start = (i - size/2) * tile_size
                y_start = (j - size/2) * tile_size
                x_end = x_start + tile_size
                y_end = y_start + tile_size

                # Añadir vértices
                tile_vertices = [
                    [x_start, y_start, 0],
                    [x_end, y_start, 0],
                    [x_end, y_end, 0],
                    [x_start, y_end, 0]
                ]
                vertices.extend(tile_vertices)

                # Añadir caras
                faces.extend([
                    [vertex_count, vertex_count + 1, vertex_count + 2],
                    [vertex_count, vertex_count + 2, vertex_count + 3]
                ])

                # Añadir colores de caras
                face_colors.extend([color, color])

                vertex_count += 4

        # Crear la malla completa
        checkerboard_mesh = gl.GLMeshItem(
            vertexes=np.array(vertices),
            faces=np.array(faces),
            faceColors=np.array(face_colors),
            smooth=False,
            drawEdges=False,
            shaders="custom"
        )

        self.gl_widget.addItem(checkerboard_mesh)

    def add_robot(self):
        """ Importa los stl del modelo del robot y los añade al widget de opengl
        """
        for data in self.links:
            link_proc = self.stl_to_pyqtgraph_mesh(data["link"])
            self.gl_widget.addItem(link_proc)

    def stl_to_pyqtgraph_mesh(self, stl_file_name, scale=0.001):
        """
        Convierte un archivo STL a un GLMeshItem para PyQtGraph

        Args:
            stl_file_path: Ruta al archivo STL
            scale: Factor de escala (del URDF)
            color: Color RGBA [r, g, b, a] (opcional)

        Returns:
            GLMeshItem listo para agregar al gl_widget
        """

        # 1. Cargar el STL
        stl_mesh = mesh.Mesh.from_file(os.path.join(os.path.dirname(__file__),
                                                    "meshes",
                                                    "visual",
                                                    f"{stl_file_name}.stl"))

        # 2. Extraer vértices
        # stl_mesh.vectors tiene forma (n_triangles, 3, 3)
        # Necesitamos convertir a (n_vertices, 3)
        vertices = stl_mesh.vectors.reshape(-1, 3)

        # 3. Aplicar escala del URDF
        vertices = vertices * scale

        # 4. Crear índices de caras
        # Como cada 3 vértices forman un triángulo
        n_triangles = len(stl_mesh.vectors)
        faces = np.arange(n_triangles * 3).reshape(-1, 3)
        # 7. Crear el GLMeshItem
        gl_mesh = gl.GLMeshItem(
            vertexes=vertices,
            faces=faces,
            smooth=True,
            drawEdges=False,
            computeNormals=True,
            color=(1.0, 1.0, 1.0, 1.0),
            shader="custom"
        )

        return gl_mesh

    def custom_shader(self):
        """ Genera un shader personalizado para la simulacion
        """
        shaders.Shaders.append(ShaderProgram('custom', [
            VertexShader("""
                         varying vec3 normal;
                         void main() {
                            // compute here for use in fragment shader
                            normal = normalize(gl_NormalMatrix * gl_Normal);
                            gl_FrontColor = gl_Color;
                            gl_BackColor = gl_Color;
                            gl_Position = ftransform();
                         }
                         """),
            FragmentShader("""
                           varying vec3 normal;
                           void main() {
                           float p = dot(normal, normalize(vec3(-0.5, 1.0, 0.3)));
                           p = p < 0. ? 0. : p * 0.8;
                           vec4 color = gl_Color;
                           color.x = color.x * (0.6 + p);
                           color.y = color.y * (0.6 + p);
                           color.z = color.z * (0.6 + p);
                           gl_FragColor = color;
                           }
                           """)
        ]))
