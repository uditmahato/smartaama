import { DataGrid, GridColDef } from "@mui/x-data-grid";
import {
  Box,
  Button,
  Stack,
  Typography,
  Dialog,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import { useEffect, useState } from "react";
import { api } from "../../services/api";
import Navbar, { navLinks } from "../../components/Navbar";

type User = {
  id: string;
  full_name: string;
  email: string;
  phone_number: string;
  facility_type: string;
  working_hospital: string;
  created_at: string;
  id_card_image_path?: string; // path from backend
};

export default function PendingUsers() {
  const [rows, setRows] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  const [openImage, setOpenImage] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string>("");

  // Load pending users
  async function load() {
    setLoading(true);
    try {
      const res = await api.get("/admin/users/pending");
      setRows(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function approve(id: string) {
    await api.patch(`/admin/users/${id}/approve`);
    load();
  }

  async function reject(id: string) {
    await api.patch(`/admin/users/${id}/reject`);
    load();
  }

  // Open ID card dialog
  const handleOpenImage = (imagePath?: string) => {
    if (!imagePath) return;
    //@ts-ignore
    const fullUrl = `${import.meta.env.VITE_UPLOADS_BASE_URL}/${encodeURI(imagePath)}`;
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

  const columns: GridColDef[] = [
    { field: "full_name", headerName: "Name", flex: 1 },
    { field: "email", headerName: "Email", flex: 1 },
    { field: "phone_number", headerName: "Phone", flex: 1 },
    { field: "facility_type", headerName: "Facility", width: 120 },
    {
      field: "working_hospital",
      headerName: "Currently Working Hospital",
      flex: 1,
    },
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
          disabled={!params.row.id_card_image_path}
        >
          View
        </Button>
      ),
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 200,
      sortable: false,
      renderCell: (params) => (
        <Stack direction="row" spacing={1}>
          <Button
            color="success"
            size="small"
            variant="contained"
            onClick={() => approve(params.row.id)}
          >
            Approve
          </Button>
          <Button
            color="error"
            size="small"
            variant="contained"
            onClick={() => reject(params.row.id)}
          >
            Reject
          </Button>
        </Stack>
      ),
    },
  ];

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#F6F7FB",
        py: { xs: 2, md: 3 },
        px: { xs: 0.5, sm: 1, md: 1.5 },
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      <Navbar
        title="Pending Users"
        subtitle="Manage users who have not yet been approved"
        links={navLinks}
      />

      <div style={{ height: 600, padding: 3 }}>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50, 100]}
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
