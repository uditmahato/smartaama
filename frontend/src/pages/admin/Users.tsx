import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useEffect, useState } from "react";
import { api } from "../../services/api";
import {
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  Typography,
  Stack,
} from "@mui/material";
import Navbar, { navLinks } from "../../components/Navbar";

type User = {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  is_approved: boolean;
  facility_type: string | null;
  id_card_image_path?: string; // path from backend
};

export default function Users() {
  const [rows, setRows] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [openImage, setOpenImage] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string>("");

  // Load users from backend
  async function load() {
    setLoading(true);
    try {
      const res = await api.get("/admin/users");
      setRows(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  // Delete user
  async function remove(id: string) {
    if (!confirm("Delete this user?")) return;
    await api.delete(`/admin/users/${id}`);
    load();
  }

  // Open dialog with image
  const handleOpenImage = (imagePath?: string) => {
    if (!imagePath) return;

    // Build full URL from env variable
    const fullUrl = imagePath.startsWith("http")
      ? imagePath
      : //@ts-ignore
        `${import.meta.env.VITE_UPLOADS_BASE_URL}/${encodeURIComponent(imagePath)}`;

    setSelectedImage(fullUrl);
    setOpenImage(true);
  };

  const handleCloseImage = () => {
    setOpenImage(false);
    setSelectedImage("");
  };

  useEffect(() => {
    load();
  }, []);

  // Define table columns
  const columns: GridColDef[] = [
    { field: "username", headerName: "Username", flex: 1 },
    { field: "email", headerName: "Email", flex: 1 },
    { field: "role", headerName: "Role", width: 140 },
    { field: "facility_type", headerName: "Facility", width: 120 },
    { field: "facility_name", headerName: "Facility Name", width: 120 },
    //nmc
    { field: "nmc_number", headerName: "NMC Number", flex: 1 },
    {
      field: "id_card",
      headerName: "ID Card",
      width: 120,
      sortable: false,
      renderCell: (params) => (
        <Button
          size="small"
          variant="outlined"
          onClick={() => handleOpenImage(params.row.id_card_image_path)}
          disabled={!params.row.id_card_image_path} // disable if no image
        >
          View
        </Button>
      ),
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 140,
      sortable: false,
      renderCell: (params) => (
        <Button
          color="error"
          size="small"
          variant="contained"
          onClick={() => remove(params.row.id)}
        >
          Delete
        </Button>
      ),
    },
  ];

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#F6F7FB", py: 3, px: 2 }}>
      <Navbar
        title="Users"
        subtitle="Manage users and their roles"
        links={navLinks}
      />

      <div style={{ height: 600, padding: 3 }}>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50, 100]} // include 100 to avoid MUI warning
          disableRowSelectionOnClick
        />
      </div>

      {/* Dialog to show ID card */}
      <Dialog
        open={openImage}
        onClose={handleCloseImage}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>ID Card</DialogTitle>
        <DialogContent>
          {selectedImage ? (
            <img
              src={selectedImage}
              alt="ID Card"
              style={{ width: "100%", height: "auto" }}
            />
          ) : (
            <Typography>No image available</Typography>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
}
