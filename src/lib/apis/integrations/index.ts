import { WEBUI_API_BASE_URL } from '$lib/constants';

const handleJsonResponse = async (res: Response) => {
	if (!res.ok) {
		throw await res.json();
	}

	return res.json();
};

const getErrorDetail = (err: any) => {
	return err?.detail || err?.message || 'Request failed';
};

export const getSourcesConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sources/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateSourcesConfig = async (token: string, body: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sources/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const syncGDrive = async (token: string, body: object = {}) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/gdrive/sync`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getGDriveFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/gdrive/files`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteGDriveFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/gdrive/files`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const syncSharePoint = async (token: string, body: object = {}) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sharepoint/sync`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSharePointFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sharepoint/files`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteSharePointFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sharepoint/files`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSharePointSites = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations/sharepoint/sites`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(handleJsonResponse)
		.catch((err) => {
			error = getErrorDetail(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
