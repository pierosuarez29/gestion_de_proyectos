let desplazamientoActual = 0;

function desplazar(direccion) {
    const numProductosVisibles = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--num-productos-visibles'));
    const catalogo = document.querySelector('.catalogo');
    const productoAncho = document.querySelector('.producto').offsetWidth + 20; // Ancho del producto + margen
    const catalogoAncho = catalogo.scrollWidth;
    const contenedorAncho = document.querySelector('.catalogo-contenedor').offsetWidth;

    desplazamientoActual += direccion * productoAncho;

    // Limitar el desplazamiento
    if (desplazamientoActual < 0) {
        desplazamientoActual = 0;
    } else if (desplazamientoActual > catalogoAncho - contenedorAncho) {
        desplazamientoActual = catalogoAncho - contenedorAncho;
    }

    catalogo.style.transform = `translateX(-${desplazamientoActual}px)`;
}
