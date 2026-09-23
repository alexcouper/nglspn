import { api, type User } from "@/lib/api";
import { AVATAR_SIZE } from "@/lib/avatarBlob";
import { putToPresignedUrl } from "@/lib/uploadImage";

// Reserve → PUT → complete, against the current user's avatar endpoints. The
// blob is the square renderAvatarBlob produced, so the dimensions reported on
// completion are known without decoding it again.
export async function uploadAvatar(blob: Blob): Promise<User> {
  const presigned = await api.auth.getAvatarUploadUrl("avatar.jpg", blob.type, blob.size);
  await putToPresignedUrl(presigned, blob);
  return api.auth.completeAvatarUpload(presigned.image_id, {
    width: AVATAR_SIZE,
    height: AVATAR_SIZE,
  });
}
