$(document).ready(function() {
    function updateProducts() {
        var query = $('#search').val();
        var filters = [];
        $('input[name="filter"]:checked').each(function() {
            filters.push($(this).val());
        });
        var sort = $('#sort').val();
        $.ajax({
            url: verProductosUrl,
            method: 'GET',
            data: {
                search: query,
                filter: filters,
                sort: sort
            },
            success: function(data) {
                $('#productos').html(data);
            },
            error: function(xhr, status, error) {
                console.error('Error en la solicitud AJAX:', status, error);
            }
        });
    }

    // Llamar a la función updateProducts en caso de cambios en los filtros, búsqueda o selección de ordenación
    $('#search').on('input', updateProducts);
    $('input[name="filter"]').on('change', updateProducts);
    $('#sort').on('change', updateProducts);

    // Opcional: Llamar a updateProducts cuando la página se cargue para mostrar productos inicialmente
    updateProducts();
});
