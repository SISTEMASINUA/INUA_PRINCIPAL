-- Esquema de base de datos para Sistema de Asistencia NFC
-- Base de datos: asistencia_nfc

-- Tabla de ubicaciones
CREATE TABLE ubicaciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    activa BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar ubicaciones predefinidas
INSERT INTO ubicaciones (nombre, activa) VALUES 
('Tepanecos', TRUE),
('Lerdo', TRUE),
('Destino', FALSE);

-- Tabla de empleados
CREATE TABLE empleados (
    id SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(255) NOT NULL,
    cargo VARCHAR(100) NOT NULL,
    rol VARCHAR(100) NOT NULL,
    nfc_uid VARCHAR(50) UNIQUE,
    foto_path VARCHAR(500),
    hora_entrada TIME NOT NULL DEFAULT '09:00:00',
    hora_salida TIME NOT NULL DEFAULT '18:00:00',
    activo BOOLEAN DEFAULT TRUE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de registros de asistencia
CREATE TABLE registros_asistencia (
    id SERIAL PRIMARY KEY,
    empleado_id INTEGER REFERENCES empleados(id),
    ubicacion_id INTEGER REFERENCES ubicaciones(id),
    fecha DATE NOT NULL,
    hora_registro TIMESTAMP NOT NULL,
    tipo_movimiento VARCHAR(20) NOT NULL CHECK (tipo_movimiento IN ('ENTRADA', 'SALIDA')),
    estado VARCHAR(20) NOT NULL CHECK (estado IN ('A_TIEMPO', 'RETARDO', 'TEMPRANO', 'FALTA')),
    sincronizado BOOLEAN DEFAULT FALSE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para almacenamiento local cuando no hay internet
CREATE TABLE registros_locales (
    id SERIAL PRIMARY KEY,
    empleado_id INTEGER,
    ubicacion_id INTEGER,
    fecha DATE NOT NULL,
    hora_registro TIMESTAMP NOT NULL,
    tipo_movimiento VARCHAR(20) NOT NULL,
    estado VARCHAR(20) NOT NULL,
    procesado BOOLEAN DEFAULT FALSE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de configuraciones del sistema
CREATE TABLE configuraciones (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) UNIQUE NOT NULL,
    valor VARCHAR(500) NOT NULL,
    descripcion VARCHAR(255),
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar configuraciones predefinidas
INSERT INTO configuraciones (clave, valor, descripcion) VALUES 
('tolerancia_entrada', '10', 'Minutos de tolerancia para entrada'),
('admin_password', 'admin123', 'Contraseña de administrador'),
('ubicacion_actual', 'Tepanecos', 'Ubicación actual del sistema');

-- Índices para mejorar rendimiento
CREATE INDEX idx_registros_empleado_fecha ON registros_asistencia(empleado_id, fecha);
CREATE INDEX idx_registros_fecha ON registros_asistencia(fecha);
CREATE INDEX idx_empleados_nfc ON empleados(nfc_uid);
CREATE INDEX idx_registros_sincronizado ON registros_asistencia(sincronizado);

-- Vista para reportes diarios
CREATE VIEW vista_asistencia_diaria AS
SELECT 
    e.nombre_completo,
    e.cargo,
    r.fecha,
    r.hora_registro,
    r.tipo_movimiento,
    r.estado,
    u.nombre as ubicacion
FROM registros_asistencia r
JOIN empleados e ON r.empleado_id = e.id
JOIN ubicaciones u ON r.ubicacion_id = u.id
ORDER BY r.fecha DESC, r.hora_registro DESC;

-- Vista para el primer y último registro del día
CREATE VIEW vista_resumen_diario AS
SELECT 
    e.id as empleado_id,
    e.nombre_completo,
    r.fecha,
    MIN(CASE WHEN r.tipo_movimiento = 'ENTRADA' THEN r.hora_registro END) as primera_entrada,
    MAX(CASE WHEN r.tipo_movimiento = 'SALIDA' THEN r.hora_registro END) as ultima_salida,
    MIN(CASE WHEN r.tipo_movimiento = 'ENTRADA' THEN r.estado END) as estado_entrada,
    MAX(CASE WHEN r.tipo_movimiento = 'SALIDA' THEN r.estado END) as estado_salida
FROM empleados e
LEFT JOIN registros_asistencia r ON e.id = r.empleado_id
GROUP BY e.id, e.nombre_completo, r.fecha
ORDER BY r.fecha DESC, e.nombre_completo;