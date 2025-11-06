-- Create the merged table
CREATE TABLE IF NOT EXISTS public."X" (
    nis VARCHAR(20),
    name VARCHAR(100),
    class VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS public."XI" (
    nis VARCHAR(20),
    name VARCHAR(100),
    class VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS public."XII" (
    nis VARCHAR(20),
    name VARCHAR(100),
    class VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS public."students" (
    nis VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    grade VARCHAR(10) NOT NULL,
    class VARCHAR(10) NOT NULL,
    room VARCHAR(10) NOT NULL
);

-- Insert data from each table with the class info


INSERT INTO X (nis, name, class)
SELECT nis, name, 'E1' AS class FROM public."XE1"
UNION ALL
SELECT nis, name, 'E2' AS class FROM public."XE2"
UNION ALL
SELECT nis, name, 'E3' AS class FROM public."XE3"
UNION ALL
SELECT nis, name, 'E4' AS class FROM public."XE4"
UNION ALL
SELECT nis, name, 'E5' AS class FROM public."XE5"
UNION ALL
SELECT nis, name, 'E6' AS class FROM public."XE6"
UNION ALL
SELECT nis, name, 'E7' AS class FROM public."XE7"
UNION ALL
SELECT nis, name, 'E8' AS class FROM public."XE8"
UNION ALL
SELECT nis, name, 'E9' AS class FROM public."XE9"
;

INSERT INTO XI (nis, name, class)
SELECT nis, name, 'F1' AS class FROM public."XIF1"
UNION ALL
SELECT nis, name, 'F2' AS class FROM public."XIF2"
UNION ALL
SELECT nis, name, 'F3' AS class FROM public."XIF3"
UNION ALL
SELECT nis, name, 'F4' AS class FROM public."XIF4"
UNION ALL
SELECT nis, name, 'F5' AS class FROM public."XIF5"
UNION ALL
SELECT nis, name, 'F6' AS class FROM public."XIF6"
UNION ALL
SELECT nis, name, 'F7' AS class FROM public."XIF7"
UNION ALL
SELECT nis, name, 'F8' AS class FROM public."XIF8"
UNION ALL
SELECT nis, name, 'F9' AS class FROM public."XIF9"
;


INSERT INTO XII (nis, name, class)
SELECT nis, name, 'F1' AS class FROM public."XIIF1"
UNION ALL
SELECT nis, name, 'F2' AS class FROM public."XIIF2"
UNION ALL
SELECT nis, name, 'F3' AS class FROM public."XIIF3"
UNION ALL
SELECT nis, name, 'F4' AS class FROM public."XIIF4"
UNION ALL
SELECT nis, name, 'F5' AS class FROM public."XIIF5"
UNION ALL
SELECT nis, name, 'F6' AS class FROM public."XIIF6"
UNION ALL
SELECT nis, name, 'F7' AS class FROM public."XIIF7"
UNION ALL
SELECT nis, name, 'F8' AS class FROM public."XIIF8"
;

INSERT INTO public."XII" (nis, name, grade, class, room)
SELECT nis, name, 'X', class, '1' FROM public."X"
UNION ALL
SELECT nis, name, 'XI', class, '1' FROM public."XI"
UNION ALL
SELECT nis, name, 'XII', class, '1' FROM public."XII"
;