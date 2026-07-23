function toggleUpload(show) {
    const area = document.getElementById('area-upload');
    const lblVazio = document.getElementById('label-vazio');
    const lblCsv = document.getElementById('label-csv');
    if (show) {
        area.classList.remove('hidden');
        lblCsv.classList.add('border-blue-200', 'bg-blue-50/50');
        lblCsv.classList.remove('border-gray-200', 'bg-white');
        lblVazio.classList.remove('border-blue-200', 'bg-blue-50/50');
        lblVazio.classList.add('border-gray-200', 'bg-white');
    } else {
        area.classList.add('hidden');
        lblCsv.classList.remove('border-blue-200', 'bg-blue-50/50');
        lblCsv.classList.add('border-gray-200', 'bg-white');
        lblVazio.classList.add('border-blue-200', 'bg-blue-50/50');
        lblVazio.classList.remove('border-gray-200', 'bg-white');
    }
}

