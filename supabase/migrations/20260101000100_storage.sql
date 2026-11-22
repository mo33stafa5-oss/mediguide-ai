-- Private buckets. Object path convention: <user_id>/<document_id>/<filename>
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types) values
  ('xray-images',       'xray-images',       false, 20971520, array['image/jpeg','image/png']),
  ('ecg-reports',       'ecg-reports',       false, 20971520, array['image/jpeg','image/png','application/pdf']),
  ('lab-reports',       'lab-reports',       false, 20971520, array['image/jpeg','image/png','application/pdf']),
  ('prescriptions',     'prescriptions',     false, 20971520, array['image/jpeg','image/png','application/pdf']),
  ('general-documents', 'general-documents', false, 20971520, array['image/jpeg','image/png','application/pdf'])
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

create policy medical_files_owner_select on storage.objects for select to authenticated
  using (bucket_id in ('xray-images','ecg-reports','lab-reports','prescriptions','general-documents')
         and (storage.foldername(name))[1] = auth.uid()::text);
create policy medical_files_owner_insert on storage.objects for insert to authenticated
  with check (bucket_id in ('xray-images','ecg-reports','lab-reports','prescriptions','general-documents')
         and (storage.foldername(name))[1] = auth.uid()::text);
create policy medical_files_owner_delete on storage.objects for delete to authenticated
  using (bucket_id in ('xray-images','ecg-reports','lab-reports','prescriptions','general-documents')
         and (storage.foldername(name))[1] = auth.uid()::text);
